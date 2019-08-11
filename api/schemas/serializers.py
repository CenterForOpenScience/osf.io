from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    IDField,
    TypeField,
    LinksField,
    RelationshipField,
)

class SchemaSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    name = ser.CharField(read_only=True)
    schema_version = ser.IntegerField(read_only=True)
    schema = ser.DictField(read_only=True)
    active = ser.BooleanField(read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        type_ = 'schemas'


class RegistrationSchemaFormBlockSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    help_text = ser.CharField(read_only=True, allow_blank=True)
    answer_id = ser.CharField(max_length=255)
    chunk_id = ser.CharField(max_length=255)
    block_type = ser.CharField(read_only=True)
    display_text = ser.CharField(allow_blank=True)

    required = ser.BooleanField(read_only=True)
    index = ser.IntegerField(required=False, read_only=True, source='_order')

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        type_ = 'form_blocks'


class RegistrationSchemaSerializer(SchemaSerializer):
    form_blocks = RelationshipField(
        related_view='schemas:registration-schema-form-blocks',
        related_view_kwargs={'schema_id': '<_id>'},
        always_embed=True,
    )

    filterable_fields = ['active']

    class Meta:
        type_ = 'registration_schemas'


class FileMetadataSchemaSerializer(SchemaSerializer):

    class Meta:
        type_ = 'file_metadata_schemas'


class DeprecatedMetaSchemaSerializer(SchemaSerializer):

    class Meta:
        type_ = 'metaschemas'


class DeprecatedRegistrationMetaSchemaSerializer(SchemaSerializer):

    class Meta:
        type_ = 'registration_metaschemas'
