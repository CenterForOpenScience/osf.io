import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from framework.celery_tasks import app as celery_app
from transitions import MachineError

from osf.models import SchemaResponse
from osf.utils.workflows import ApprovalStates

from website.settings import REGISTRATION_UPDATE_APPROVAL_TIME

logger = logging.getLogger(__name__)

THRESHOLD_HOURS = int(REGISTRATION_UPDATE_APPROVAL_TIME.total_seconds() / 3600)

@celery_app.task(name='osf.management.commands.approve_pending_schema_responses')
@transaction.atomic
def approve_pending_schema_responses(dry_run=False):
    '''Migrate registration_responses into a SchemaResponse for historical registrations.'''
    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Auto-Approving SchemaResponses submitted longer than {THRESHOLD_HOURS} hours ago'
    )
    # Get all non-initial SchemaResponses that have been pending Admin Approval
    # for longer than the environment's auto-approval threshold
    auto_approval_threshold = timezone.now() - REGISTRATION_UPDATE_APPROVAL_TIME
    pending_schema_responses = SchemaResponse.objects.filter(
        reviews_state=ApprovalStates.UNAPPROVED.db_name,
        submitted_timestamp__lte=auto_approval_threshold,
        previous_response__isnull=False,
    )
    count = 0

    for schema_response in pending_schema_responses:
        logger.info(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'Auto-approving SchemaResponse with id [{schema_response._id}] '
            f'for Registration with guid [{schema_response.parent._id}]'
        )
        try:
            schema_response.accept(
                comment=f'Auto-approved following {THRESHOLD_HOURS} hour threshhold'
            )
        except MachineError:
            logger.exception(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Error auto-approving SchemaResponse with id [{schema_response._id}] '
                f'for Registration with guit [{schema_response.parent._id}]'
            )
        else:
            count += 1

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back')

    return count


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        approve_pending_schema_responses(dry_run=dry_run)
