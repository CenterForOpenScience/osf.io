# -*- coding: utf-8 -*-
import os
import json

import jsonschema
from django.db import models

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from addons.osfstorage.models import OsfStorageFile
from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.metaschema import FileMetadataSchema
from osf.utils import permissions as osf_permissions
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.metadata.serializers import serializer_registry
from website.util import api_v2_url


def validate_user_entered_metadata(value):
    # TODO - consolodate this code which is from api.users.schemas.utils.from_json
    here = os.path.split(os.path.abspath(__file__))[0]
    with open(os.path.join(here, '../metadata/schemas/user_entered_datacite.json')) as f:
        user_entered_schema = json.load(f)
    # If validation fails, this will throw a validation error
    return jsonschema.validate(value, user_entered_schema)


class FileMetadataRecord(ObjectIDMixin, BaseModel):

    metadata = DateTimeAwareJSONField(default=dict, blank=True, validators=[validate_user_entered_metadata])

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

            # If we've made it this far, log!
            target = self.file.target
            target.add_log(
                action='file_metadata_updated',
                # TODO: do these params need to be changed?
                params={
                    'project': target.parent_id,
                    'node': target._id,
                },
                auth=auth,
            )
        else:
            raise PermissionsError('You must have write access for this file to update its metadata.')
