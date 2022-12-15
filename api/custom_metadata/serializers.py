import logging

from rdflib import DCTERMS
from django.core.validators import URLValidator
import rest_framework.serializers as ser

from api.base.serializers import JSONAPISerializer, RelationshipField, IDField
from osf.models.metadata import CustomMetadataProperty


logger = logging.getLogger(__name__)


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
    id = IDField(read_only=True, source='guid._id')
    guid = RelationshipField(
        read_only=True,
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'}
    )
    language = ser.CharField(required=False)  # TODO: choices
    resource_type_general = ser.CharField(required=False)  # TODO: choices
    funders = FundingInfoSerializer(
        many=True,
        source='funding_info',
        required=False,
    )
    custom_properties = CustomMetadataPropertySerializer(
        many=True,
        source='custom_property_set',
        required=False,
    )

    def update(self, guid_metadata_record, validated_data):
        logger.critical(f'valdat: {validated_data}')
        for field_name in ('language', 'resource_type_general', 'funding_info'):
            if field_name in validated_data:
                setattr(guid_metadata_record, field_name, validated_data[field_name])
        guid_metadata_record.full_clean()
        guid_metadata_record.save()

        validated_custom_property_set = validated_data.get('custom_property_set', None)
        if validated_custom_property_set is not None:
            to_create = [
                CustomMetadataProperty(
                    metadata_record=guid_metadata_record,
                    property_uri=validated_property['property_uri'],
                    value_as_text=validated_property['value_as_text'],
                )
                for validated_property in validated_custom_property_set
            ]
            # wipe out and recreate -- it's the only (...easiest) way to be sure
            guid_metadata_record.custom_property_set.all().delete()
            CustomMetadataProperty.objects.bulk_create(to_create)

        return guid_metadata_record


class CustomItemMetadataSerializer(GuidMetadataRecordSerializer):
    class Meta:
        type_ = 'custom-item-metadata-record'


class CustomMetadataPropertyProxyField(ser.Field):
    def __init__(self, property_uri, **kwargs):
        self._property_uri = property_uri
        super().__init__(**kwargs, source='*')

    def to_representation(self, metadata_record):
        return (
            CustomMetadataProperty.objects
            .filter(metadata_record=metadata_record)
            .filter(property_uri=self._property_uri)
            .values_list('value_as_text', flat=True)
            .first()
        )

    def to_internal_value(self, data):
        proxied_serializer = CustomMetadataPropertySerializer(
            data={
                'property_uri': self._property_uri,
                'value_as_text': data,
            },
        )
        proxied_serializer.is_valid()
        return {self.field_name: proxied_serializer.validated_data}


class CustomFileMetadataSerializer(GuidMetadataRecordSerializer):
    title = CustomMetadataPropertyProxyField(DCTERMS.title, required=False)
    description = CustomMetadataPropertyProxyField(DCTERMS.description, required=False)

    class Meta:
        type_ = 'custom-file-metadata-record'

    def update(self, guid_metadata_record, validated_data):
        additional_custom_properties = []
        for field_name in ('title', 'description'):
            validated_custom_property = validated_data.pop(field_name, None)
            if validated_custom_property is not None:
                additional_custom_properties.append(validated_custom_property)
        validated_data.setdefault('custom_properties', []).extend(additional_custom_properties)
        return super().update(guid_metadata_record, validated_data)
