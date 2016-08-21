from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField


class TaxonomySerializer(JSONAPISerializer):
    filterable_fields = frozenset([
        'text',
        'parents',
        'id'
    ])
    id = ser.CharField(source='_id', required=True)
    text = ser.CharField(max_length=200)
    parents = ser.SerializerMethodField(method_name='get_parent_ids')

    links = LinksField({
        'parents': 'get_parent_urls',
        'self': 'get_absolute_url',
    })

    def get_parent_ids(self, obj):
        return [p._id for p in obj.parents]

    def get_parent_urls(self, obj):
        return [p.get_absolute_url() for p in obj.parents]

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    class Meta:
        type_ = 'taxonomies'
