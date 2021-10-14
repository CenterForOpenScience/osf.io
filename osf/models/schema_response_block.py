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
    def create(cls, source_response, source_block, response_value=None):
        new_response_block = cls(
            source_schema_response=source_response,
            source_Schema_block=source_block,
            schema_key=source_block.registration_response_key
        )
        new_response_block.set_response(response_value)
        return new_response_block

    @cached_property
    def block_type(self):
        return self.source_schema_block.block_type

    @cached_property
    def required(self):
        return self.source_schema_block.required

    def _get_select_input_options(self):
        group_key = self.source_block.schema_block_group_key
        allowed_values = self.source_block.schema.schema_blocks.filter(
            schema_block_group_key=group_key, block_type='select-input-option'
        ).values_list('display_text', flat=True)
        return list(allowed_values)

    def is_valid(self, check_required=True):
        '''Confirms that the block has been assigned a valid value.'''
        block_type = self.block_type
        if not isinstance(self.response, SUPPORTED_TYPE_FOR_BLOCK_TYPE[block_type]):
            return False

        if block_type in ['single-select-input', 'multi-select-input']:
            responses = self.response
            if block_type == 'single-select-input':  # listify `single-select-ninput` response value
                responses = [responses] if responses else []
            allowed_options = self._get_select_input_options()
            if not all(response in allowed_options for response in responses):
                return False
        elif self.block_type == 'file-input':
            pass  # TODO have somebody who understands this add validation

        if check_required and self.required and not self.response:
            return False

        return True

    def set_response(self, response_value=None):
        if response_value is None:
            response_value = SUPPORTED_TYPE_FOR_BLOCK_TYPE[self.block_type]()
        self.response = sanitize.strip_html(response_value)
        if not self.is_valid(check_required=False):
            raise SchemaResponseUpdateError(invalid_responses={self.schema_key: response_value})
        self.save()
