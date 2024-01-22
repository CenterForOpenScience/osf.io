import logging

from django.db import IntegrityError
from rest_framework import serializers as ser

from api.base.exceptions import InvalidModelValueError, JSONAPIException
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField
from api.base.utils import absolute_reverse

from osf.exceptions import ValidationError
from osf.models import CedarMetadataRecord, CedarMetadataTemplate, Guid

logger = logging.getLogger(__name__)


class GuidRelationshipField(RelationshipField):

    def get_object(self, _id):
        return Guid.load(_id)

    def to_internal_value(self, data):
        return self.get_object(data)


class CedarMetadataTemplateRelationshipField(RelationshipField):

    def get_object(self, _id):
        return CedarMetadataTemplate.load(_id)

    def to_internal_value(self, data):
        return self.get_object(data)


class CedarMetadataRecordsSerializer(JSONAPISerializer):

    class Meta:
        type_ = 'cedar-metadata-records'

    filterable_fields = frozenset(['is_published'])

    id = ser.CharField(source='_id', read_only=True)

    guid = RelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'},
        # always_embed=True,
        read_only=True,
    )

    template = RelationshipField(
        related_view='cedar-metadata-templates:cedar-metadata-template-detail',
        related_view_kwargs={'template_id': '<template._id>'},
        # always_embed=True,
        read_only=True,
    )

    metadata = ser.DictField(read_only=False)

    is_published = ser.BooleanField(read_only=False)

    links = LinksField({'self': 'get_absolute_url'})

    def get_absolute_url(self, obj):
        return absolute_reverse('cedar-metadata-records:cedar-metadata-record-detail', kwargs={'record_id': obj._id})

    def update(self, instance, validated_data):
        assert isinstance(instance, CedarMetadataRecord), 'instance must be a CedarMetadataRecord'
        for key, value in validated_data.items():
            if key == 'metadata':
                instance.metadata = value
            elif key == 'is_published':
                instance.is_published = value
            else:
                continue  # ignore other attributes
        instance.save()
        return instance


class CedarMetadataRecordsCreateSerializer(CedarMetadataRecordsSerializer):

    guid = GuidRelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'},
        read_only=False,
        required=True,
    )

    template = CedarMetadataTemplateRelationshipField(
        related_view='cedar-metadata-templates:cedar-metadata-template-detail',
        related_view_kwargs={'template_id': '<template._id>'},
        read_only=False,
        required=True,
    )

    metadata = ser.DictField(read_only=False, required=True)

    is_published = ser.BooleanField(read_only=False, required=True)

    def create(self, validated_data):

        guid = validated_data.pop('guid')
        template = validated_data.pop('template')
        metadata = validated_data.pop('metadata')
        is_published = validated_data.pop('is_published')
        record = CedarMetadataRecord(guid=guid, template=template, metadata=metadata, is_published=is_published)
        try:
            record.save()
        except ValidationError as e:
            raise InvalidModelValueError(detail=e.messages[0])
        except IntegrityError:
            raise JSONAPIException(detail=f'Cedar metadata record already exists: guid=[{guid._id}], template=[{template._id}]')
        return record
