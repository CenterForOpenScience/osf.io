from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    IDField,
    TypeField,
    LinksField,
    RelationshipField,
)
from api.base.versioning import get_kebab_snake_case_field

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


class AbstractSchemaBlockSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    response_key = ser.CharField(read_only=True)
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
        type_ = 'schema-blocks'


class RegistrationSchemaBlockSerializer(AbstractSchemaBlockSerializer):

    schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<schema._id>'},
    )


class FileSchemaBlockSerializer(AbstractSchemaBlockSerializer):

    schema = RelationshipField(
        related_view='schemas:file-schema-detail',
        related_view_kwargs={'schema_id': '<schema._id>'},
    )


class RegistrationSchemaSerializer(SchemaSerializer):
    description = ser.CharField(read_only=True, allow_blank=True)

    schema_blocks = RelationshipField(
        related_view='schemas:registration-schema-block-list',
        related_view_kwargs={'schema_id': '<_id>'},
    )

    filterable_fields = ['active']

    class Meta:
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'registration-schemas')


class FileSchemaSerializer(SchemaSerializer):

    schema_blocks = RelationshipField(
        related_view='schemas:file-schema-block-list',
        related_view_kwargs={'schema_id': '<_id>'},
    )

    class Meta:
        @staticmethod
        def get_type(request):
            return get_kebab_snake_case_field(request.version, 'file-schemas')
