# -*- coding: utf-8 -*-
import jsonschema
from django.db import models

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from addons.osfstorage.models import OsfStorageFile
from api.base.schemas.utils import from_json
from osf.models import NodeLog
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.metaschema import FileMetadataSchema
from osf.utils import permissions as osf_permissions
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.metadata.serializers import serializer_registry
from website.util import api_v2_url


def validate_user_entered_metadata(value):
    return jsonschema.validate(value, from_json('user_entered_datacite.json'))


class FileMetadataRecord(ObjectIDMixin, BaseModel):

    metadata = DateTimeAwareJSONField(default=dict, blank=True, validators=[validate_user_entered_metadata])

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

    def validate(self):
        # causes model level validation to run
        self.clean_fields()
        return self.serializer.validate(self)

    def update(self, proposed_metadata, user=None):
        auth = Auth(user) if user else None
        if auth and self.file.target.has_permission(user, osf_permissions.WRITE):
            self.metadata = proposed_metadata
            self.validate()
            self.save()

            target = self.file.target
            target.add_log(
                action=NodeLog.FILE_METADATA_UPDATED,
                params={
                    'project': target.parent_id,
                    'node': target._id,
                    'file': self.file._id
                },
                auth=auth,
            )
        else:
            raise PermissionsError('You must have write access for this file to update its metadata.')
