import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from framework.celery_tasks import app as celery_app
from transitions import MachineError

from osf.models import CollectionSubmission, OSFUser
from osf.utils.workflows import CollectionSubmissionStates

logger = logging.getLogger(__name__)

DEFAULT_COMMENT = 'This collection submission has been rejected.'


@celery_app.task(name='osf.management.commands.reject_pending_collection_submissions')
def reject_pending_collection_submissions(user_guid, comment, dry_run=False):
    comment = comment or DEFAULT_COMMENT
    user = OSFUser.load(user_guid)
    if not user:
        raise RuntimeError(f'Could not find user with guid {user_guid!r}.')

    pending_submissions = CollectionSubmission.objects.filter(
        machine_state=CollectionSubmissionStates.PENDING.value
    ).select_related('collection__provider', 'guid', 'creator')

    total = pending_submissions.count()
    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Found {total} pending collection submission(s) to reject.'
    )

    rejected_count = 0
    error_count = 0
    for submission in pending_submissions.iterator():
        guid = submission.guid._id if submission.guid else 'unknown'
        try:
            # Each submission commits independently: a failure here rolls back this submission, not others  already processed.
            with transaction.atomic():
                submission.reject(user=user, comment=comment, force=True)
                if dry_run:
                    transaction.set_rollback(True)
        except MachineError:
            logger.exception(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'MachineError rejecting CollectionSubmission for node guid [{guid}]'
            )
            error_count += 1
        except Exception:
            logger.exception(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Error rejecting CollectionSubmission for node guid [{guid}]'
            )
            error_count += 1
        else:
            rejected_count += 1
            logger.info(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Rejected CollectionSubmission for node guid [{guid}]'
            )

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Done. Rejected {rejected_count}/{total} submission(s), {error_count} error(s).'
    )

    return rejected_count


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--user',
            dest='user_guid',
            required=True,
            help='GUID of the user to use as the rejection action creator.',
        )
        parser.add_argument(
            '--comment',
            dest='comment',
            default=DEFAULT_COMMENT,
            help='Comment to attach to each rejection action.',
        )
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run — rolls back all changes.',
        )

    def handle(self, *args, **options):
        try:
            rejected_count = reject_pending_collection_submissions(
                user_guid=options['user_guid'],
                comment=options['comment'],
                dry_run=options['dry_run'],
            )
        except RuntimeError as e:
            raise CommandError(str(e))

        prefix = '[DRY RUN] ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(f'{prefix}Rejected {rejected_count} submission(s).'))
