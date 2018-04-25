from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField


class RegionSerializer(JSONAPISerializer):
    id = ser.CharField(source='_id', read_only=True)
    name = ser.CharField(read_only=True)

    links = LinksField({
        'self': 'get_absolute_url'
    })

    class Meta:
        type_ = 'storage_regions'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url
