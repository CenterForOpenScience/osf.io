import rest_framework.serializers as ser

from osf.metadata import rdfutils
from api.base.serializers import JSONAPISerializer, RelationshipField


# TODO: max_lengths, uri validation


class BaseCustomMetadataSerializer(JSONAPISerializer):
    def to_representation(self, guid_metadata_record):
        pass  # TODO: from rdf graph to dict

    def to_internal_value(self, data):
        pass  # TODO: from dict to rdf graph


class FunderSerializer(ser.Serializer):
    funder_name = ser.CharField()
    funder_identifier = ser.CharField()
    funder_identifier_type = ser.CharField()
    award_number = ser.CharField()
    award_uri = ser.CharField()
    award_title = ser.CharField()


class CustomItemMetadataSerializer(JSONAPISerializer):
    language = ser.CharField()  # TODO: choices
    resource_type_general = ser.CharField()  # TODO: choices
    funder = ser.ListField(child=FunderSerializer())

    guid = RelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'}
    )

    class Meta:
        type_ = 'custom-item-metadata-record'


class CustomFileMetadataSerializer(JSONAPISerializer):
    title = ser.CharField()
    description = ser.CharField()
    language = ser.CharField()  # TODO: choices
    resource_type_general = ser.CharField()  # TODO: choices

    guid = RelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'}
    )

    class Meta:
        type_ = 'custom-file-metadata-record'
