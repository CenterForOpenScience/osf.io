# -*- coding: utf-8 -*-
import rdflib
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.functional import cached_property

from framework.auth.core import Auth
from framework.exceptions import PermissionsError
from osf.metadata import rdfutils
from osf.models.base import BaseModel, ObjectIDMixin, Guid, InvalidGuid
from osf.utils import permissions as osf_permissions


class GuidMetadataRecordManager(models.Manager):
    def for_guid(self, guid, allowed_referent_models=None):
        guid_qs = Guid.objects.all().select_related('metadata_record')
        if isinstance(guid, str):
            guid_qs = guid_qs.filter(_id=guid)
        elif isinstance(guid, Guid):
            guid_qs = guid_qs.filter(_id=guid._id)
        else:
            raise InvalidGuid(f'expected str or Guid, got {guid} (of type {type(guid)})')

        if allowed_referent_models is not None:
            allowed_content_types = set(
                ContentType.objects
                .get_for_models(*allowed_referent_models)
                .values()
            )
            guid_qs = guid_qs.filter(content_type__in=allowed_content_types)

        try:
            found_guid = guid_qs.get()
        except Guid.DoesNotExist:
            raise InvalidGuid(
                f'guid does not exist: {guid}',
            )
        try:
            return found_guid.metadata_record
        except GuidMetadataRecord.DoesNotExist:
            # new, unsaved GuidMetadataRecord
            return GuidMetadataRecord(guid=found_guid)


class GuidMetadataRecord(ObjectIDMixin, BaseModel):
    guid = models.OneToOneField('Guid', related_name='metadata_record', on_delete=models.CASCADE)

    # TODO: validator using osf-map and pyshacl?
    custom_metadata_bytes = models.BinaryField(default=b'{}')  # serialized rdflib.Graph
    _RDF_FORMAT = 'json-ld'

    objects = GuidMetadataRecordManager()

    def __repr__(self):
        return f'{self.__class__.__name__}(guid={self.guid._id})'

    @cached_property
    def custom_metadata(self) -> rdflib.Graph:
        return rdfutils.contextualized_graph().parse(
            format=self._RDF_FORMAT,
            data=self.custom_metadata_bytes,
        )

    def save(self, *args, **kwargs):
        # the cached custom_metadata graph may have been updated
        self.custom_metadata_bytes = self.custom_metadata.serialize(format=self._RDF_FORMAT)
        super().save(*args, **kwargs)

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
