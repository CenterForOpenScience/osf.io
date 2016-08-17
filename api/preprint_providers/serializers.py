from rest_framework import serializers as ser

from website.settings import API_DOMAIN
from api.base.settings.defaults import API_BASE
from api.base.serializers import JSONAPISerializer, LinksField

class PreprintProviderSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'name',
        'description',
        'id'
    ])

    name = ser.CharField(required=True)
    description = ser.CharField(required=False)
    id = ser.CharField(max_length=200, source='_id')

    logo_path = ser.CharField(read_only=True)
    banner_path = ser.CharField(read_only=True)

    links = LinksField({
        'self': 'get_absolute_url',
        'preprints': 'preprint_links'
    })

    class Meta:
        type_ = 'preprint_providers'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def preprint_links(self, obj):
        return '{}{}preprint_providers/{}/preprints/'.format(API_DOMAIN, API_BASE, obj._id)
