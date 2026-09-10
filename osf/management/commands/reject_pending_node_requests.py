import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from framework.celery_tasks import app as celery_app
from transitions import MachineError

from osf.models import NodeRequest, OSFUser
from osf.utils.workflows import NodeRequestTypes

logger = logging.getLogger(__name__)

DEFAULT_COMMENT = 'This project is now read-only, so this access request has been automatically rejected.'

NODE_REQUEST_TYPES_TO_REJECT = [
    NodeRequestTypes.ACCESS.value,
    NodeRequestTypes.INSTITUTIONAL_REQUEST.value,
]


@celery_app.task(name='osf.management.commands.reject_pending_node_requests')
def reject_pending_node_requests(user_guid, comment, dry_run=False):
    comment = comment or DEFAULT_COMMENT
    user = OSFUser.load(user_guid)
    if not user:
        raise RuntimeError(f'Could not find user with guid {user_guid!r}.')

    pending_requests = NodeRequest.objects.filter(
        machine_state='pending',
        request_type__in=NODE_REQUEST_TYPES_TO_REJECT,
    ).select_related('target', 'creator')

    total = pending_requests.count()
    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Found {total} pending node request(s) to reject.'
    )

    rejected_count = 0
    error_count = 0
    for node_request in pending_requests.iterator():
        guid = node_request._id
        try:
            # Each request commits independently: a failure here rolls back this request, not others already processed.
            with transaction.atomic():
                node_request.run_reject(user=user, comment=comment)
                if dry_run:
                    transaction.set_rollback(True)
        except MachineError:
            logger.exception(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'MachineError rejecting NodeRequest [{guid}]'
            )
            error_count += 1
        except Exception:
            logger.exception(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Error rejecting NodeRequest [{guid}]'
            )
            error_count += 1
        else:
            rejected_count += 1
            logger.info(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Rejected NodeRequest [{guid}]'
            )

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Done. Rejected {rejected_count}/{total} node request(s), {error_count} error(s).'
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
            rejected_count = reject_pending_node_requests(
                user_guid=options['user_guid'],
                comment=options['comment'],
                dry_run=options['dry_run'],
            )
        except RuntimeError as e:
            raise CommandError(str(e))

        prefix = '[DRY RUN] ' if options['dry_run'] else ''
        self.stdout.write(self.style.SUCCESS(f'{prefix}Rejected {rejected_count} node request(s).'))
