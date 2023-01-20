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
        to_record = GuidMetadataRecord.objects.for_guid(to_guid)
        to_record.title = from_record.title
        to_record.description = from_record.description
        to_record.language = from_record.language
        to_record.resource_type_general = from_record.resource_type_general
        to_record.funding_info = from_record.funding_info
        to_record.save()


class GuidMetadataRecord(ObjectIDMixin, BaseModel):
    guid = models.OneToOneField('Guid', related_name='metadata_record', on_delete=models.CASCADE)

    # TODO: consider consolidating title/description/etc. metadata fields from many
    #       models (perhaps replace EditableFieldsMixin with a model like this)
    title = models.TextField(blank=True)
    description = models.TextField(blank=True)
    language = models.TextField(blank=True)  # TODO: choices?
    resource_type_general = models.TextField(blank=True)  # TODO: choices?

    FUNDER_INFO_JSONSCHEMA = {
        'type': 'array',
        'items': {
            'type': 'object',
            'required': [],
            'minProperties': 1,
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

    def get_editable_fields(self):
        from osf.models.files import BaseFileNode
        editable_fields = {
            'language',
            'resource_type_general',
            'funding_info',
        }
        if isinstance(self.guid.referent, BaseFileNode):
            editable_fields.update(('title', 'description'))
        return editable_fields

    def update(self, new_values, auth):
        updated_fields = {}
        editable_fields = self.get_editable_fields()
        for field_name, new_value in new_values.items():
            if field_name not in editable_fields:
                raise ValueError(f'cannot update `{field_name}` on {self}')
            updated_fields[field_name] = {
                'old': getattr(self, field_name),
                'new': new_value,
            }
            setattr(self, field_name, new_value)
        self.save()
        self._log_update(auth, updated_fields)
        if hasattr(self.guid.referent, 'update_search'):
            self.guid.referent.update_search()

    def _log_update(self, auth, updated_fields):
        from osf.models.files import BaseFileNode
        from osf.models.preprint import Preprint
        loggable_referent = self.guid.referent
        log_params = {
            'updated_fields': updated_fields,
            'guid': self.guid._id,
            'urls': {
                'view': f'/{self.guid._id}',
            },
        }
        if isinstance(loggable_referent, BaseFileNode):
            log_params['path'] = loggable_referent.materialized_path
            loggable_referent = loggable_referent.target
            log_action = loggable_referent.log_class.FILE_METADATA_UPDATED
        else:
            log_action = loggable_referent.log_class.GUID_METADATA_UPDATED

        if isinstance(loggable_referent, Preprint):
            log_params['preprint'] = loggable_referent._id
        else:
            log_params['node'] = loggable_referent._id

        loggable_referent.add_log(
            action=log_action,
            params=log_params,
            auth=auth,
        )
