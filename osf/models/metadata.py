# -*- coding: utf-8 -*-
from django.db import models

from addons.osfstorage.models import OsfStorageFile
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.metaschema import FileMetadataMetaSchema
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class FileMetadataRecord(ObjectIDMixin, BaseModel):

    metadata = DateTimeAwareJSONField(default=dict, blank=True)

    file = models.ForeignKey(OsfStorageFile, related_name='records', on_delete=models.SET_NULL, null=True)
    schema = models.ForeignKey(FileMetadataMetaSchema, related_name='records', on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('file', 'schema')

    def format(self, type='json'):
        return self.schema.formatter.format(self.file, self.metadata, type)

    def validate(self, data):
        return self.schema.formatter.validate(self, data)
