import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from api.schema_responses import annotations
from osf.models import SchemaResponse
from website.archiver.utils import migrate_file_metadata


logger = logging.getLogger(__name__)


@transaction.atomic
def fix_initial_schema_responses(dry_run=False, batch_size=None):
    '''SchemaResponses were released into the wild not fully ready. Fix the ones with early issues.

    This command should delete SchemaResponses from non-root Registrations and fix file-input
    responses that were not updated post-archival and point to the Node instead of the Registration.
    '''
    # TODO: filter for only registrations?
    qs = SchemaResponse.objects.annotate(
        is_original_response=annotations.IS_ORIGINAL_RESPONSE
    ).filter(
        is_original_response=True
    ).order_by('schema__id')

    corrected_schema_response_count = 0
    deleted_schema_response_count = 0

    for schema_response in qs[:batch_size or None]:  # don't allow 0 batch_size
        parent = schema_response.parent
        if parent.root_id != parent.id:
            logger.info(
                f'{"[DRY RUN] " if dry_run else ""}'
                f'Deleting SchemaResponses for non-root registration with guid [{parent._id}]'
            )
            parent_schema_response_count = parent.schema_responses.count()
            deleted_schema_response_count += parent_schema_response_count
            if not dry_run:
                parent.schema_responses.all().delete()
            continue

        logger.info(
            f'{"[DRY RUN] " if dry_run else ""}'
            f'Updating file references for  SchemaResponses with id [{schema_response._id}] '
            f'on parent Registration with guid [{parent._id}]'
        )
        migrate_file_metadata(parent)
        corrected_schema_response_count += 1

    if dry_run:
        raise RuntimeError('Dry run, transaction rolled back')

    return corrected_schema_response_count, deleted_schema_response_count


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
        fix_initial_schema_responses(dry_run=dry_run, batch_size=batch_size)
