from rest_framework import serializers as ser

from api.base.serializers import (
    IDField,
    JSONAPISerializer,
    RelationshipField,
    TypeField
)


class FileMetadataSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    metadata = ser.SerializerMethodField()

    schema = RelationshipField(
        related_view='metaschemas:metaschema-detail',
        related_view_kwargs={'metaschema_id': '<schema._id>'}
    )

    file = RelationshipField(
        related_view='files:file-detail',
        related_view_kwargs={'file_id': '<file._id>'}
    )

    class Meta:
        type_ = 'metadata_records'

    def get_metadata(self, obj):
        return obj.format()

    def update(self, instance, validated_data):
        # TODO: finish me
        try:
            instance.validate(validated_data)
        except Exception:
            pass
        instance.metadata = validated_data
        instance.save()
        return instance
