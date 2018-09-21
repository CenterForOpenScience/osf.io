# -*- coding: utf-8 -*-
from django.db import models

from addons.osfstorage.models import OsfStorageFile
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.metaschema import FileMetadataSchema
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.metadata.serializers import serializer_registry
from website.util import api_v2_url


class FileMetadataRecord(ObjectIDMixin, BaseModel):

    metadata = DateTimeAwareJSONField(default=dict, blank=True)

    file = models.ForeignKey(OsfStorageFile, related_name='records', on_delete=models.SET_NULL, null=True)
    schema = models.ForeignKey(FileMetadataSchema, related_name='records', on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('file', 'schema')

    @property
    def absolute_api_v2_url(self):
        path = '/files/{}/metadata_records/{}/'.format(self.file._id, self._id)
        return api_v2_url(path)

    @property
    def serializer(self):
        return serializer_registry[self.schema._id]

    def serialize(self, format='json'):
        return self.serializer.serialize(self, format)

    def validate(self, proposed_metadata):
        return self.serializer.validate(self, proposed_metadata)

    def update(self, proposed_metadata):
        if self.validate(proposed_metadata):
            return self.serializer.update(self, proposed_metadata)
