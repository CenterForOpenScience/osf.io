# -*- coding: utf-8 -*-
import rdflib
from django.db import models

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils import permissions as osf_permissions


class GuidMetadataRecordManager(models.Manager):
    def for_guid(self, guid):
        try:
            return guid.metadata_record
        except GuidMetadataRecord.DoesNotExist:
            return self.model(guid=guid)


class GuidMetadataRecord(ObjectIDMixin, BaseModel):

    guid = models.OneToOneField('Guid', related_name='metadata_record', on_delete=models.CASCADE)

    # TODO: validator using osf-map and pyshacl
    custom_metadata_bytes = models.BinaryField(default=b'{}')  # serialized json
    # compiled_metadata_jsonld = DateTimeAwareJSONField(default=dict, blank=True)

    objects = GuidMetadataRecordManager()

    def __repr__(self):
        return f'{self.__class__.__name__}(guid={self.guid._id})'

    @property
    def custom_metadata_graph(self):
        # TODO: bind namespaces
        return rdflib.Graph().parse(
            format='json-ld',
            data=self.custom_metadata_bytes,
        )

    @custom_metadata_graph.setter
    def custom_metadata_graph(self, graph):
        self.custom_metadata_bytes = graph.serialize(format='json-ld')

    # TODO: either something like this, or delete this
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
