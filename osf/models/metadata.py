# -*- coding: utf-8 -*-
import jsonschema
from django.db import models

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from addons.osfstorage.models import OsfStorageFile
from api.base.schemas.utils import from_json
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.metaschema import FileMetadataSchema
from osf.utils import permissions as osf_permissions
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.metadata.serializers import serializer_registry
from website.util import api_v2_url


class FileMetadataRecord(ObjectIDMixin, BaseModel):

    metadata = DateTimeAwareJSONField(default=dict, blank=True)

    file = models.ForeignKey(OsfStorageFile, related_name='records', on_delete=models.SET_NULL, null=True)
    schema = models.ForeignKey(FileMetadataSchema, related_name='records', on_delete=models.SET_NULL, null=True)

    class Meta:
        unique_together = ('file', 'schema')

    def __unicode__(self):
        return '(file={}, schema={}, _id={})'.format(self.file.name, self.schema, self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/files/{}/metadata_records/{}/'.format(self.file._id, self._id)
        return api_v2_url(path)

    @property
    def serializer(self):
        return serializer_registry[self.schema._id]

    def serialize(self, format='json'):
        return self.serializer.serialize(self, format)

    def validate_metadata(self, proposed_metadata):
        return jsonschema.validate(proposed_metadata, from_json(self.serializer.osf_schema))

    def update(self, proposed_metadata, user=None):
        auth = Auth(user) if user else None
        if auth and self.file.target.has_permission(user, osf_permissions.WRITE):
            self.validate_metadata(proposed_metadata)
            self.metadata = proposed_metadata
            self.save()

            target = self.file.target
            target.add_log(
                action=target.log_class.FILE_METADATA_UPDATED,
                params={
                    'path': self.file.materialized_path,
                },
                auth=auth,
            )
        else:
            raise PermissionsError('You must have write access for this file to update its metadata.')
