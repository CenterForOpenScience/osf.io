from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField
from api.base.utils import absolute_reverse


class BrandSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)

    hero_logo_image = ser.URLField(read_only=True)
    topnav_logo_image = ser.URLField(read_only=True)
    hero_background_image = ser.URLField(read_only=True)

    primary_color = ser.CharField(read_only=True, max_length=7)
    secondary_color = ser.CharField(read_only=True, max_length=7)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'brands:brand-detail',
            kwargs={
                'brand_id': obj.id,
                'version': 'v2',
            },
        )

    class Meta:
        type_ = 'brands'
