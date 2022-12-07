import logging

from django.core.management.base import BaseCommand
from osf.utils.workflows import CollectionSubmissionStates

from osf.models import CollectionSubmission

logger = logging.getLogger(__name__)


def collection_submission_machine_state_backfill(*args, backfill_date=None, dry_run=False, **kwargs):
    submissions = CollectionSubmission.objects.all()

    logger.info(f'{submissions.count()} submissions to backfill')
    if not dry_run:
        if backfill_date:
            submissions.filter(
                date_created__lte=backfill_date,
                collection__deleted__isnull=True,
            ).update(
                machine_state=CollectionSubmissionStates.ACCEPTED
            )
        else:
            submissions.filter(
                collection__deleted__isnull=True,
            ).update(
                machine_state=CollectionSubmissionStates.ACCEPTED
            )


def reverse_collection_submission_machine_state_backfill(*args, backfill_date=None, dry_run=False, **kwargs):
    submissions = CollectionSubmission.objects.all()

    logger.info(f'{submissions.count()} submissions to reverse backfill')
    if not dry_run:
        if backfill_date:
            submissions.filter(
                date_created__lte=backfill_date,
                collection__deleted__isnull=True,
            ).update(
                machine_state=CollectionSubmissionStates.IN_PROGRESS
            )
        else:
            submissions.update(
                machine_state=CollectionSubmissionStates.IN_PROGRESS
            )


class Command(BaseCommand):
    """
    Backfill machine states for collection submissions this will put all collection submissions in the system into an
    `Accepted` state, putting them "into" the collections they are currently associated with.
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Run migration and roll back changes to db',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        collection_submission_machine_state_backfill(dry_run)
