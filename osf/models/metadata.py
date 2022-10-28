# -*- coding: utf-8 -*-
from django.db import models

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from osf.metadata import rdfutils
from osf.models.base import BaseModel, ObjectIDMixin, Guid
from osf.utils import permissions as osf_permissions


class GuidMetadataRecordManager(models.Manager):
    def for_guid(self, guid):
        if isinstance(guid, str):
            guid = Guid.load(guid)
        if not guid:
            return None  # TODO: would it be better to raise?
        try:
            return guid.metadata_record
        except GuidMetadataRecord.DoesNotExist:
            # new, unsaved GuidMetadataRecord
            return GuidMetadataRecord(guid=guid)


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
        return rdfutils.contextualized_graph().parse(
            format='json-ld',
            data=self.custom_metadata_bytes,
        )

    @custom_metadata_graph.setter
    def custom_metadata_graph(self, graph):
        self.custom_metadata_bytes = graph.serialize(format='json-ld')

    # TODO: safety, logging
    def add_custom_metadatum(self, property_iri, value):
        rdf_graph = self.custom_metadata_graph
        rdf_graph.set((rdfutils.guid_irl(self.guid), property_iri, value))
        self.custom_metadata_graph = rdf_graph
        self.save()

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
