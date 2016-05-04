from rest_framework import serializers as ser
from api.base.serializers import (JSONAPISerializer, IDField, TypeField, LinksField)


class MetaSchemaSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    name = ser.CharField(read_only=True)
    schema_version = ser.IntegerField(read_only=True)
    schema = ser.DictField(read_only=True)

    links = LinksField({})

    class Meta:
        type_ = 'meta_schemas'
