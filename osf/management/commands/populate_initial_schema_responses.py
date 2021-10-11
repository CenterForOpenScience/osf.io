import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, F, OuterRef

from osf.exceptions import DryRun, PreviousSchemaResponseError, UnsupportedSchemaKeysError
from osf.models import Registration, SchemaResponse
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates

logger = logging.getLogger(__name__)

# Registrations have not previously been validated for unsupported keys,
# some past backfills/migrations have created known mismatches. Handle these.
EXPECTED_UNSUPPORTED_KEYS = {'EGAP Registration': {'q2'}, 'Prereg Challenge': {'q2'}}


def _update_schema_response_state(schema_response):
    '''Set the schema_response's state based on the current state of the parent rgistration.'''
    moderation_state = schema_response.parent.moderation_state
    if moderation_state == RegistrationModerationStates.INITIAL.db_name:
        schema_response.state = ApprovalStates.UNAPPROVED
    elif moderation_state == RegistrationModerationStates.PENDING.db_name:
        schema_response.state = ApprovalStates.PENDING_MODERATION
    else:
        # All remaining states mean the initial responses have been approved by users
        # (or else the Registration will be excluded by our filters)
        schema_response.state = ApprovalStates.APPROVED
    schema_response.save()

def populate_initial_schema_responses(dry_run=False, batch_size=None):
    '''Migrate registration_responses into a SchemaResponse for historical registrations.'''
    # Find all root registrations that do not yet have SchemaResponses
    qs = Registration.objects.prefetch_related('root').annotate(
        has_schema_response=Exists(SchemaResponse.objects.filter(nodes__id=OuterRef('id')))
    ).filter(
        has_schema_response=False, root=F('id'), deleted__isnull=True
    )
    if batch_size:
        qs = qs[:batch_size]

    count = 0
    for registration in qs:
        logger.info(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'Creating initial SchemaResponses for Registration with guid {registration._id}'
        )
        try:
            with transaction.atomic():
                try:
                    registration.copy_registration_responses_into_schema_response()
                except UnsupportedSchemaKeysError as e:
                    schema_name = registration.registration_schema.name
                    if not e.keys.issubset(EXPECTED_UNSUPPORTED_KEYS.get(schema_name, set())):
                        raise e
                _update_schema_response_state(registration.schema_responses.last())
                count += 1
                if dry_run:
                    raise DryRun
        except (ValueError, PreviousSchemaResponseError, UnsupportedSchemaKeysError):
            logger.exception(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Failure creating SchemaResponse for Registration with guid {registration._id}'
            )
        except DryRun:
            pass

    logger.info(
        f'{"[DRY RUN] " if dry_run else ""}'
        f'Created initial SchemaResponses for {count} registrations'
    )

    return count


class Command(BaseCommand):
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
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
        try:
            with transaction.atomic():
                populate_initial_schema_responses(dry_run=dry_run, batch_size=batch_size)
        except DryRun:
            pass
