from django.db import models
from django.utils.functional import cached_property

from osf.exceptions import SchemaResponseUpdateError
from osf.models import RegistrationSchemaBlock
from .base import BaseModel, ObjectIDMixin
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
        related_name='updated_response_blocks',
        on_delete=models.CASCADE,
    )
    # Must align with the `registration_response_key from some schema_block on the
    # source_schema_response's schema
    schema_key = models.CharField(max_length=255)
    response = DateTimeAwareJSONField(blank=True, null=True)

    class Meta:
        unique_together = ('source_schema_response', 'schema_key')

    @classmethod
    def create(cls, source_schema_response, source_schema_block, response_value=None):
        new_response_block = cls(
            source_schema_response=source_schema_response,
            schema_key=source_schema_block.registration_response_key
        )
        new_response_block.set_response(response_value)
        return new_response_block

    @cached_property
    def source_schema_block(self):
        return RegistrationSchemaBlock.objects.filter(
            schema=self.source_schema_response.schema,
            registration_response_key=self.schema_key
        ).get()

    @cached_property
    def block_type(self):
        return self.source_schema_block.block_type

    @cached_property
    def required(self):
        return self.source_schema_block.required

    def set_response(self, response_value=None):
        '''Set the response for the block.

        Validates and sanitizes the value before assigning.
        Assigns a sane default for the block type if no value or a
        False-equivalent value is passed.
        '''
        if not response_value:
            response_value = SUPPORTED_TYPE_FOR_BLOCK_TYPE[self.block_type]()
        if not self.is_valid(response_value, check_required=False):
            raise SchemaResponseUpdateError(
                response=self.source_schema_response,
                invalid_responses={self.schema_key: response_value})
        self.response = _sanitize_response(response_value, self.block_type)
        self.save()

    def is_valid(self, response_value=None, check_required=True):
        '''Confirms that a response value is valid for this block.'''
        if response_value is None:
            response_value = self.response
        block_type = self.block_type
        if not isinstance(response_value, SUPPORTED_TYPE_FOR_BLOCK_TYPE[block_type]):
            return False
        if not self._has_valid_selections(response_value):
            return False
        if check_required and self.required and not response_value:
            return False

        return True

    def _has_valid_selections(self, response_value):
        '''Validate the contents of a `*-select-input` block.'''
        block_type = self.block_type
        if block_type not in ['single-select-input', 'multi-select-input']:
            return True

        # Listify the response value
        values = response_value
        if block_type == 'single-select-input':
            values = [values] if values else []

        if not values:  # validation of required fields occurs elsewhere
            return True

        allowed_options = self._get_select_input_options()
        return all(entry in allowed_options for entry in values)

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
