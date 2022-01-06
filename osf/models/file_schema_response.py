from django.db import models

from api.base.utils import absolute_reverse

from osf.models.schema_response import AbstractSchemaResponse
from osf.models.schema_block import FileSchemaBlock
from osf.models.schema_response_block import FileSchemaResponseBlock


class FileSchemaResponse(AbstractSchemaResponse):
    '''...'''
    schema = models.ForeignKey('osf.FileSchema')
    response_blocks = models.ManyToManyField('osf.SchemaResponseBlock')
    initiator = models.ForeignKey('osf.OsfUser', null=False)
    parent = models.ForeignKey(
        'osf.OsfStorageFile',
        related_name='schema_responses',
        on_delete=models.SET_NULL,
        null=True
    )

    @property
    def absolute_api_v2_url(self):
        return absolute_reverse(
            'files:file_schema_responses:file-schema-response-detail',
            kwargs={
                'version': 'v2',
                'file_id': self.parent._id,
                'file_schema_response_id': self._id,
            },
        )

    @property
    def responses(self):
        '''Surfaces responses from response_blocks in a dictionary format'''
        return {
            response_block.schema_key: response_block.response
            for response_block in self.response_blocks.all()
        }

    def set_responses(self, responses):
        question_blocks = FileSchemaBlock.objects.filter(
            schema=self.schema,
            response_key__isnull=False
        )
        for source_block in question_blocks:
            block = FileSchemaResponseBlock.objects.get_or_create(
                source_schema_response=self,
                schema_key=source_block.schema_key,
            )
            block.set_response(responses['schema_key'])
