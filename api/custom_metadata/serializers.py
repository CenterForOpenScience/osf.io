import rest_framework.serializers as ser

from framework.auth.core import Auth
from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    LinksField,
    RelationshipField,
)
from api.base.utils import absolute_reverse


# TODO: max_lengths, uri validation


class FundingInfoListSerializer(ser.ListSerializer):
    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)

        # quietly remove funding-infos with all blank values
        def not_all_blank(funding_info):
            return not all(
                value == ''
                for value in funding_info.values()
            )
        return list(filter(not_all_blank, validated_data))


class FundingInfoSerializer(ser.Serializer):
    funder_name = ser.CharField(allow_blank=True, default='')
    funder_identifier = ser.CharField(allow_blank=True, default='')
    funder_identifier_type = ser.CharField(allow_blank=True, default='')
    award_number = ser.CharField(allow_blank=True, default='')
    award_uri = ser.CharField(allow_blank=True, default='')
    award_title = ser.CharField(allow_blank=True, default='')

    class Meta:
        list_serializer_class = FundingInfoListSerializer


class CustomItemMetadataSerializer(JSONAPISerializer):
    non_anonymized_fields = {
        'id',
        'guid',
        'resource_type_general',
        'language',
    }

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
        'self': 'get_absolute_url',
    })

    class Meta:
        type_ = 'custom-item-metadata-records'

    def update(self, guid_metadata_record, validated_data):
        user = self.context['request'].user
        guid_metadata_record.update(validated_data, Auth(user))
        return guid_metadata_record

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'custom-item-metadata:custom-item-metadata-detail', kwargs={
                'guid_id': obj.guid._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class CustomFileMetadataSerializer(CustomItemMetadataSerializer):
    non_anonymized_fields = CustomItemMetadataSerializer.non_anonymized_fields | {
        'title',
        'description',
    }

    title = ser.CharField(required=False, allow_blank=True)  # TODO: max-length
    description = ser.CharField(required=False, allow_blank=True)  # TODO: max-length

    class Meta:
        type_ = 'custom-file-metadata-records'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'custom-file-metadata:custom-file-metadata-detail', kwargs={
                'guid_id': obj.guid._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )
