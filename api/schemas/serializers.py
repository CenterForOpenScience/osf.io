from rest_framework import serializers as ser
from api.base.serializers import (JSONAPISerializer, IDField, TypeField, LinksField)
from distutils.version import StrictVersion

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


class RegistrationSchemaSerializer(SchemaSerializer):

    filterable_fields = ['active']

    class Meta:
        @staticmethod
        def get_type(request):
            if StrictVersion(request.version) < StrictVersion('2.15'):
                return 'registration_schemas'
            return 'registration-schemas'


class FileMetadataSchemaSerializer(SchemaSerializer):

    class Meta:
        @staticmethod
        def get_type(request):
            if StrictVersion(request.version) < StrictVersion('2.15'):
                return 'file_metadata_schemas'
            return 'file-metadata-schemas'


class DeprecatedMetaSchemaSerializer(SchemaSerializer):

    class Meta:
        type_ = 'metaschemas'


class DeprecatedRegistrationMetaSchemaSerializer(SchemaSerializer):

    class Meta:
        type_ = 'registration_metaschemas'
