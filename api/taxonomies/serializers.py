from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, LinksField, IDField, TypeField
)

class TaxonomySerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    data = ser.CharField()

    class Meta:
        type_ = 'taxonomies'
