# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction

from osf.models.base import (
    BaseModel,
    Guid,
    GuidMixin,
    InvalidGuid,
    ObjectIDMixin,
    OptionalGuidMixin,
)
from osf.models.validators import JsonschemaValidator


class MetadataRecordCopyConflict(Exception):
    pass


def coerce_guid(maybe_guid, create_if_needed=False):
    if isinstance(maybe_guid, Guid):
        return maybe_guid
    if isinstance(maybe_guid, GuidMixin):
        return maybe_guid.guids.first()
    if isinstance(maybe_guid, OptionalGuidMixin):
        return maybe_guid.get_guid(create=create_if_needed)
    raise NotImplementedError(f'cannot coerce into Guid: {maybe_guid}')


class GuidMetadataRecordManager(models.Manager):
    def for_guid(self, guid, allowed_referent_models=None):
        """get a GuidMetadataRecord instance for the given osf:Guid.

        @param guid: `str` or `osf.models.Guid` instance
        @param allowed_referent_models: (optional) iterable of model classes
        @returns `GuidMetadataRecord` instance (unsaved unless it already existed)
        @raises `InvalidGuid` if the given guid does not exist (or refers to
                a type not in the given `allowed_referent_models`)
        """
        guid_qs = (
            Guid.objects.all()
            .select_related('metadata_record')
        )
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

    @transaction.atomic
    def copy(self, from_, to_):
        from_guid = coerce_guid(from_)
        if from_guid is None:
            return  # nothing to copy; all good
        try:
            from_record = GuidMetadataRecord.objects.get(guid=from_guid)
        except GuidMetadataRecord.DoesNotExist:
            return  # nothing to copy; all good

        to_guid = coerce_guid(to_, create_if_needed=True)
        if GuidMetadataRecord.objects.filter(guid=to_guid).exists():
            raise MetadataRecordCopyConflict(f'cannot copy GuidMetadataRecord to {to_guid}; it already has one!')
        to_record = GuidMetadataRecord(
            guid=to_guid,
            language=from_record.language,
            resource_type_general=from_record.resource_type_general,
            funding_info=from_record.funding_info,
        )
        to_record.save()


class GuidMetadataRecord(ObjectIDMixin, BaseModel):
    guid = models.OneToOneField('Guid', related_name='metadata_record', on_delete=models.CASCADE)

    title = models.TextField(blank=True)  # TODO: handle unnecessarily redundant duplication
    description = models.TextField(blank=True)  # TODO: handle unnecessarily redundant duplication
    language = models.TextField(blank=True)  # TODO: choices?
    resource_type_general = models.TextField(blank=True)  # TODO: choices?

    FUNDER_INFO_JSONSCHEMA = {
        'type': 'array',
        'items': {
            'type': 'object',
            'required': [],
            'additionalProperties': False,
            'properties': {
                'funder_name': {'type': 'string'},
                'funder_identifier': {'type': 'string'},
                'funder_identifier_type': {'type': 'string'},
                'award_number': {'type': 'string'},
                'award_uri': {'type': 'string'},
                'award_title': {'type': 'string'},
            },
        },
    }
    funding_info = models.JSONField(
        default=list,
        blank=True,
        validators=[JsonschemaValidator(FUNDER_INFO_JSONSCHEMA)],
    )

    objects = GuidMetadataRecordManager()

    def __repr__(self):
        return f'{self.__class__.__name__}(guid={self.guid._id})'

    # TODO: something like this
    # def update(self, proposed_metadata, user=None):
    #     auth = Auth(user) if user else None
    #     if auth and self.file.target.has_permission(user, osf_permissions.WRITE):
    #         self.validate_metadata(proposed_metadata)
    #         self.metadata = proposed_metadata
    #         self.save()

    #         target = self.file.target
    #         target.add_log(
    #             action=target.log_class.FILE_METADATA_UPDATED,
    #             params={
    #                 'path': self.file.materialized_path,
    #             },
    #             auth=auth,
    #         )
    #     else:
    #         raise PermissionsError('You must have write access for this file to update its metadata.')
