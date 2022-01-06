from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin
from api.base.utils import absolute_reverse
from osf.models import SchemaResponseBlock
from osf.models.schema_response import AbstractSchemaResponse


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

    @responses.setter
    def responses(self, value):
        '''Surfaces responses from response_blocks in a dictionary format'''
        self.schema.validate_metadata(value)
        blocks = SchemaResponseBlock.objects.get(source_schema_response=self)
        for block, data in zip(blocks, list(value)):
            block.set_response(data)
