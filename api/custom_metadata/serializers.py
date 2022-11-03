import rest_framework.serializers as ser

from osf.metadata import rdfutils
from api.base.serializers import JSONAPISerializer, RelationshipField, IDField


# TODO: max_lengths, uri validation


class MetadataPredicateField(ser.Field):
    def __init__(self, *args, predicate_uri, **kwargs):
        self.predicate_uri = predicate_uri
        return super().__init__(*args, **kwargs)

    def to_representation(self, value):
        # TODO: use osf-map/owl to decide one v many
        values = list(value)
        if not values:
            return None
        elif len(values) == 1:
            return values[0]
        else:
            return values

    def get_attribute(self, metadata_record):
        guid_uri = rdfutils.OSFIO[metadata_record.guid._id]
        return metadata_record.custom_metadata.objects(
            subject=guid_uri,
            predicate=self.predicate_uri,
        )


class BaseCustomMetadataSerializer(JSONAPISerializer):
    id = IDField(read_only=True, source='guid._id')
    guid = RelationshipField(
        related_view='guids:guid-detail',
        related_view_kwargs={'guids': '<guid._id>'}
    )

    def update(self, guid_metadata_record, validated_data):
        pass  # TODO


class FunderSerializer(ser.Serializer):
    funder_name = ser.CharField()
    funder_identifier = ser.CharField()
    funder_identifier_type = ser.CharField()
    award_number = ser.CharField()
    award_uri = ser.CharField()
    award_title = ser.CharField()


class CustomItemMetadataSerializer(BaseCustomMetadataSerializer):
    language = MetadataPredicateField(predicate_uri=rdfutils.DCT.language)  # TODO: choices
    resource_type_general = MetadataPredicateField(predicate_uri=rdfutils.DCT.type)  # TODO: choices
    # funder = ser.ListField(child=FunderSerializer())

    class Meta:
        type_ = 'custom-item-metadata-record'


class CustomFileMetadataSerializer(BaseCustomMetadataSerializer):
    title = MetadataPredicateField(predicate_uri=rdfutils.DCT.title)
    description = MetadataPredicateField(predicate_uri=rdfutils.DCT.description)
    language = MetadataPredicateField(predicate_uri=rdfutils.DCT.language)  # TODO: choices
    resource_type_general = MetadataPredicateField(predicate_uri=rdfutils.DCT.type)  # TODO: choices

    class Meta:
        type_ = 'custom-file-metadata-record'
