from rest_framework import serializers as ser

from api.base.utils import absolute_reverse
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField


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

    preprints = RelationshipField(
        related_view='preprint_providers:preprints-list',
        related_view_kwargs={'provider_id': '<_id>'}
    )

    links = LinksField({
        'self': 'get_absolute_url',
        'preprints': 'get_preprints_url',
        'external_url': 'get_external_url'
    })

    class Meta:
        type_ = 'preprint_providers'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_preprints_url(self, obj):
        return absolute_reverse('preprint_providers:preprints-list', kwargs={
            'provider_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_external_url(self, obj):
        return obj.external_url
