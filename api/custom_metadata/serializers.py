import rdflib
import rest_framework.serializers as ser

from osf.metadata.rdfutils import DCT, OSFIO
from api.base.serializers import JSONAPISerializer, RelationshipField, IDField


# TODO: max_lengths, uri validation


class CustomMetadataPropertyField(ser.Field):
    def __init__(self, *args, predicate_uri, **kwargs):
        self.predicate_uri = predicate_uri
        return super().__init__(*args, **kwargs)

    def get_attribute(self, metadata_record):
        guid_uri = OSFIO[metadata_record.guid._id]
        return metadata_record.custom_metadata.objects(
            subject=guid_uri,
            predicate=self.predicate_uri,
        )

    def to_representation(self, value):
        # TODO: use osf-map/owl to decide one v many
        values = list(value)
        if not values:
            return None
        elif len(values) == 1:
            return values[0]
        else:
            return values

    def to_internal_value(self, data):
        # TODO: handle nested field (FunderSerializer)
        # TODO: if controlled vocab, rdflib.URIRef
        return (self.predicate_uri, rdflib.Literal(data))


class BaseCustomMetadataSerializer(JSONAPISerializer):
    id = IDField(read_only=True, source='guid._id')
    guid = RelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'}
    )

    def update(self, guid_metadata_record, validated_data):
        for predicate_uri, value in validated_data.values():
            guid_metadata_record.set_custom_property(predicate_uri, value)
        guid_metadata_record.save()
        return guid_metadata_record

    def is_valid(self, **kwargs):
        # prevent osf hax from mangling rdflib terms into plain strings
        return super().is_valid(clean_html=False, **kwargs)


class FunderSerializer(ser.Serializer):
    funder_name = ser.CharField()
    funder_identifier = ser.CharField()
    funder_identifier_type = ser.CharField()
    award_number = ser.CharField()
    award_uri = ser.CharField()
    award_title = ser.CharField()


class CustomItemMetadataSerializer(BaseCustomMetadataSerializer):
    language = CustomMetadataPropertyField(predicate_uri=DCT.language)  # TODO: choices
    resource_type_general = CustomMetadataPropertyField(predicate_uri=DCT.type)  # TODO: choices
    # funder = ser.ListField(child=FunderSerializer())

    class Meta:
        type_ = 'custom-item-metadata-record'


class CustomFileMetadataSerializer(BaseCustomMetadataSerializer):
    title = CustomMetadataPropertyField(predicate_uri=DCT.title)
    description = CustomMetadataPropertyField(predicate_uri=DCT.description)
    language = CustomMetadataPropertyField(predicate_uri=DCT.language)  # TODO: choices
    resource_type_general = CustomMetadataPropertyField(predicate_uri=DCT.type)  # TODO: choices

    class Meta:
        type_ = 'custom-file-metadata-record'
