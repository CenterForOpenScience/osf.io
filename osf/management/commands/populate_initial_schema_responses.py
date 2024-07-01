import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, F, OuterRef
from framework.celery_tasks import app as celery_app

from osf.exceptions import PreviousSchemaResponseError, SchemaResponseUpdateError
from osf.models import Registration, SchemaResponse
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates as RegStates

logger = logging.getLogger(__name__)

# Initial response pending amin approval or rejected while awaiting it
UNAPPROVED_STATES = [RegStates.INITIAL.db_name, RegStates.REVERTED.db_name]
# Initial response pending moderator approval or rejected while awaiting it
PENDING_MODERATION_STATES = [RegStates.PENDING.db_name, RegStates.REJECTED.db_name]


def _update_schema_response_state(schema_response):
    '''Set the schema_response's state based on the current state of the parent rgistration.'''
    moderation_state = schema_response.parent.moderation_state
    if moderation_state in UNAPPROVED_STATES:
        schema_response.state = ApprovalStates.UNAPPROVED
    elif moderation_state in PENDING_MODERATION_STATES:
        schema_response.state = ApprovalStates.PENDING_MODERATION
    else:  # All remainint states imply initial responses were approved by users at some point
        schema_response.state = ApprovalStates.APPROVED
    schema_response.save()


@celery_app.task(name='management.commands.populate_initial_schema_responses')
@transaction.atomic
def populate_initial_schema_responses(dry_run=False, batch_size=None):
    '''Migrate registration_responses into a SchemaResponse for historical registrations.'''
    # Find all root registrations that do not yet have SchemaResponses
    qs = Registration.objects.prefetch_related('root').annotate(
        has_schema_response=Exists(SchemaResponse.objects.filter(nodes__id=OuterRef('id')))
    ).filter(
        has_schema_response=False, root=F('id')
    )
    if batch_size:
        qs = qs[:batch_size]

    count = 0
    for registration in qs:
        logger.info(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'Creating initial SchemaResponse for Registration with guid {registration._id}'
        )
        try:
            registration.copy_registration_responses_into_schema_response()
        except SchemaResponseUpdateError as e:
            logger.info(
                f'Ignoring unsupported values "registration_responses" for registration '
                f'with guid [{registration._id}]: {str(e)}'
            )
        except (ValueError, PreviousSchemaResponseError):
            logger.exception(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Failure creating SchemaResponse for Registration with guid {registration._id}'
            )
            # These errors should have prevented SchemaResponse creation, but better safe than sorry
            registration.schema_responses.all().delete()
            continue

        _update_schema_response_state(registration.schema_responses.last())
        count += 1

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Created initial SchemaResponses for {count} registrations'
    )

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

        parser.add_argument(
            '--batch_size',
            type=int,
            default=0
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        batch_size = options.get('batch_size')
        populate_initial_schema_responses(dry_run=dry_run, batch_size=batch_size)
