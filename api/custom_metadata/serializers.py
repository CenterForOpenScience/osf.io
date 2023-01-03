from django.core.validators import URLValidator
import rest_framework.serializers as ser

from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)
from api.base.utils import absolute_reverse


# TODO: max_lengths, uri validation


class FundingInfoSerializer(ser.Serializer):
    funder_name = ser.CharField()
    funder_identifier = ser.CharField()
    funder_identifier_type = ser.CharField()
    award_number = ser.CharField()
    award_uri = ser.CharField()
    award_title = ser.CharField()


class CustomMetadataPropertySerializer(ser.Serializer):
    property_uri = ser.CharField(validators=[URLValidator])
    value_as_text = ser.CharField()


class GuidMetadataRecordSerializer(JSONAPISerializer):
    EDITABLE_FIELDS = None  # override in subclasses

    id = IDField(read_only=True, source='guid._id')
    guid = RelationshipField(
        read_only=True,
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'},
    )
    language = ser.CharField(required=False, allow_blank=True)  # TODO: choices
    resource_type_general = ser.CharField(required=False, allow_blank=True)  # TODO: choices
    funders = FundingInfoSerializer(
        many=True,
        source='funding_info',
        required=False,
    )
    links = LinksField({
        'self': 'get_self_link',
    })

    def get_self_link(self, obj):
        raise NotImplementedError

    def update(self, guid_metadata_record, validated_data):
        for field_name in self.EDITABLE_FIELDS:
            if field_name in validated_data:
                setattr(guid_metadata_record, field_name, validated_data[field_name])
        guid_metadata_record.save()
        return guid_metadata_record


class CustomItemMetadataSerializer(GuidMetadataRecordSerializer):
    EDITABLE_FIELDS = ('language', 'resource_type_general', 'funding_info')

    class Meta:
        type_ = 'custom-item-metadata-records'

    def get_self_link(self, obj):
        return absolute_reverse(
            'custom-item-metadata:custom-item-metadata-detail', kwargs={
                'guid_id': obj.guid._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class CustomFileMetadataSerializer(GuidMetadataRecordSerializer):
    EDITABLE_FIELDS = ('title', 'description', 'language', 'resource_type_general', 'funding_info')

    title = ser.CharField(required=False, allow_blank=True)  # TODO: max-length
    description = ser.CharField(required=False, allow_blank=True)  # TODO: max-length

    class Meta:
        type_ = 'custom-file-metadata-records'

    def get_self_link(self, obj):
        return absolute_reverse(
            'custom-file-metadata:custom-file-metadata-detail', kwargs={
                'guid_id': obj.guid._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )
