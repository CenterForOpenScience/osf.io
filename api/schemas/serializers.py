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


class RegistrationSchemaBlockSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    registration_response_key = ser.CharField(read_only=True)
    schema_block_group_key = ser.CharField(read_only=True)
    block_type = ser.CharField(read_only=True)
    display_text = ser.CharField(read_only=True)
    help_text = ser.CharField(read_only=True)
    example_text = ser.CharField(read_only=True)
    required = ser.BooleanField(read_only=True)
    index = ser.IntegerField(read_only=True, source='_order')

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    class Meta:
        type_ = 'schema_blocks'


class RegistrationSchemaSerializer(SchemaSerializer):
    description = ser.CharField(read_only=True, allow_blank=True)

    schema_blocks = RelationshipField(
        related_view='schemas:registration-schema-form-blocks',
        related_view_kwargs={'schema_id': '<_id>'},
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
