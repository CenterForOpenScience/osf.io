import logging

from django.core.management.base import BaseCommand
from osf.utils.workflows import CollectionSubmissionStates

from osf.models import CollectionSubmission

logger = logging.getLogger(__name__)


def collection_submission_machine_state_backfill(*args, dry_run=False, **kwargs):
    submissions = CollectionSubmission.objects.all()

    logger.info(f'{submissions.count()} submissions to backfill')
    if not dry_run:
        submissions.update(
            machine_state=CollectionSubmissionStates.ACCEPTED
        )


def reverse_collection_submission_machine_state_backfill(*args, dry_run=False, **kwargs):
    submissions = CollectionSubmission.objects.all()

    logger.info(f'{submissions.count()} submissions to reverse backfill')
    if not dry_run:
        submissions.update(
            machine_state=CollectionSubmissionStates.IN_PROGRESS
        )


class Command(BaseCommand):
    """
    Backfill machine states for collection submissions
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
