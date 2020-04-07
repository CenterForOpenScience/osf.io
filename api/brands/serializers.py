from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField


class BrandSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'name',
    ])

    id = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)

    hero_logo_image = ser.URLField()
    topnav_logo_image = ser.URLField()
    hero_background_image = ser.URLField()

    primary_color = ser.CharField(max_length=7)
    secondary_color = ser.CharField(max_length=7)

    links = LinksField({
        'self': 'get_absolute_url',
    })

    # providers = RelationshipField(
    #     related_view='institutions:institution-nodes',
    #     related_view_kwargs={'institution_id': '<_id>'},
    # )

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    class Meta:
        type_ = 'brands'
