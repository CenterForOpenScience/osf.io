import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Exists, F, OuterRef

from osf.exceptions import DryRun, PreviousSchemaResponseError
from osf.models import Registration, SchemaResponse
from osf.utils.workflows import ApprovalStates, RegistrationModerationStates

logger = logging.getLogger(__name__)

def get_response_state_for_registration_state(moderation_state):
    if moderation_state == RegistrationModerationStates.INITIAL.db_name:
        return ApprovalStates.UNAPPROVED
    if moderation_state == RegistrationModerationStates.PENDING.db_name:
        return ApprovalStates.PENDING_MODERATION

    # All remaining states mean the initial responses have been approved by users
    # or else the Registration will be excluded by our filters
    return ApprovalStates.APPROVED

def populate_initial_schema_responses(dry_run=False, batch_size=None):
    # Find all root registrations that do not yet have SchemaResponses
    qs = Registration.objects.prefetch_related('root').annotate(
        has_schema_response=Exists(SchemaResponse.objects.filter(nodes__id=OuterRef('id')))
    ).filter(
        has_schema_response=False, root=F('id'), deleted__isnull=True
    ).exclude(
        moderation_state=RegistrationModerationStates.WITHDRAWN.db_name
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
            with transaction.atomic:
                registration.copy_schema_responses_into_initial_responses()
                response = registration.schema_responses.last()
                response.state = get_response_state_for_registration_state(
                    registration.moderation_state
                )
                response.save()
                count += 1
                if dry_run:
                    raise DryRun
        except (ValueError, PreviousSchemaResponseError):
            logger.exception(
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
        populate_initial_schema_responses(dry_run=dry_run, batch_size=batch_size)
