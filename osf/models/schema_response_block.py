from django.db import models
from django.utils.functional import cached_property

from osf.exceptions import SchemaResponseUpdateError
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils import sanitize


SUPPORTED_TYPE_FOR_BLOCK_TYPE = {
    'short-text-input': str,
    'long-text-input': str,
    'single-select-input': str,
    'multi-select-input': list,
    'contributors-input': str,
    'file-input': list,
}

class SchemaResponseBlock(ObjectIDMixin, BaseModel):

    # The SchemaResponse instance where this response originated
    source_schema_response = models.ForeignKey(
        'osf.SchemaResponse',
        null=False,
        related_name='updated_response_blocks'
    )
    # The RegistrationSchemaBlock that defines the question being answered
    source_schema_block = models.ForeignKey('osf.RegistrationSchemaBlock', null=False)

    # Should match source_schema_block.registration_response_key
    schema_key = models.CharField(max_length=255)
    response = DateTimeAwareJSONField(blank=True, null=True)

    class Meta:
        unique_together = ('source_schema_response', 'source_schema_block')

    @classmethod
    def create(cls, source_schema_response, source_schema_block, response_value=None):
        new_response_block = cls(
            source_schema_response=source_schema_response,
            source_schema_block=source_schema_block,
            schema_key=source_schema_block.registration_response_key
        )
        new_response_block.set_response(response_value)
        return new_response_block

    @cached_property
    def block_type(self):
        return self.source_schema_block.block_type

    @cached_property
    def required(self):
        return self.source_schema_block.required

    def set_response(self, response_value=None):
        if response_value is None:
            response_value = SUPPORTED_TYPE_FOR_BLOCK_TYPE[self.block_type]()
        if not self.is_valid(check_required=False):
            raise SchemaResponseUpdateError(
                response=self.source_schema_response,
                invalid_responses={self.schema_key: response_value})
        self.response = _sanitize_response(response_value, self.block_type)
        self.save()

    def is_valid_response(self, response=None, check_required=True):
        '''Confirms that the block has been assigned a valid value.'''
        if response is None:
            response = self.response
        block_type = self.block_type
        if not isinstance(response, SUPPORTED_TYPE_FOR_BLOCK_TYPE[block_type]):
            return False
        if not self._has_valid_selections(response):
            return False
        if check_required and self.required and not response:
            return False

        return True

    def _has_valid_selections(self, response):
        '''Validate the contents of a `*-select-input` block.'''
        block_type = self.block_type
        if block_type not in ['single-select-input', 'multi-select-input']:
            return True

        # Listify the response value
        responses = response
        if block_type == 'single-select-input':
            responses = [responses] if responses else []

        if not responses:  # validation of required fields occurs elsewhere
            return True

        allowed_options = self._get_select_input_options()
        return all(entry in allowed_options for entry in responses)

    def _get_select_input_options(self):
        group_key = self.source_schema_block.schema_block_group_key
        allowed_values = self.source_schema_block.schema.schema_blocks.filter(
            schema_block_group_key=group_key, block_type='select-input-option'
        ).values_list('display_text', flat=True)
        return list(allowed_values)


def _sanitize_response(response_value, block_type):
    if block_type == 'file-input':
        return response_value  # don't mess with this magic
    elif block_type == 'multi-select-input':
        return [sanitize.strip_html(entry) for entry in response_value]
    else:
        return sanitize.strip_html(response_value)
