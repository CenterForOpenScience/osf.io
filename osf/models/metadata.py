# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.db import models

from osf.models.base import BaseModel, ObjectIDMixin, Guid, InvalidGuid
from osf.models.validators import JsonschemaValidator


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


class GuidMetadataRecord(ObjectIDMixin, BaseModel):
    guid = models.OneToOneField('Guid', related_name='metadata_record', on_delete=models.CASCADE)

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
        validators=[JsonschemaValidator(FUNDER_INFO_JSONSCHEMA)],
    )

    ## implicitly defined on other models:
    # custom_property_set = OneToMany(CustomMetadataProperty)

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


class CustomMetadataProperty(ObjectIDMixin, BaseModel):
    metadata_record = models.ForeignKey(
        GuidMetadataRecord,
        related_name='custom_property_set',
        on_delete=models.CASCADE,
    )

    property_uri = models.URLField()
    value_as_text = models.TextField()
