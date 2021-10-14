import functools
import logging

from api.schema_responses import annotations
from osf.models import RegistrationSchema, SchemaResponse


logger = logging.getLogger(__name__)


@functools.lru_cache()
def _get_file_input_block_keys(schema_id):
    schema = RegistrationSchema.objects.prefetch_related('schema_blocks').get(id=schema_id)
    return set(schema.schema_blocks.filter(
        block_type='file-input'
    ).values_list(
        'registration_response_key', flat=True
    ))


def fix_initial_schema_responses(batch_size=None, dry_run=False):
    '''SchemaResponses were released into the wild not fully ready. Fix the ones with early issues.

    This command should delete SchemaResponses from non-root Registrations and fix file-input
    responses that were not updated post-archival and point to the Node instead of the Registration.
    '''
    # TODO: filter for only registrations?
    qs = SchemaResponse.objects.annotate(
        is_original_response=annotations.IS_ORIGINAL_RESPONSE
    ).filter(
        is_original_response=True
    ).order_by('object_id', 'schema__id')

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

        if schema_response._update_file_references(parent.registration_responses):
            corrected_schema_response_count += 1

    return corrected_schema_response_count, deleted_schema_response_count
