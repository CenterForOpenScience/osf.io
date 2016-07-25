from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer, LinksField, IDField, TypeField
)
from api.base.utils import absolute_reverse


class TaxonomySerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    data = ser.CharField()

    class Meta:
        type_ = 'taxonomies'

    # def get_absolute_url(self, obj):
    #     return absolute_reverse('taxonomies', kwargs={'taxonomy_id': obj._id})
