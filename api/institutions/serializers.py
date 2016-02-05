from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, RelationshipField, LinksField

class InstitutionSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'id',
        'name'
    ])

    name = ser.CharField(required=False)
    id = ser.CharField(required=False, source='_id')
    logo_path = ser.CharField()
    links = LinksField({'self': 'get_api_url',
                        'html': 'get_absolute_url', })

    nodes = RelationshipField(
        related_view='institutions:institution-nodes',
        related_view_kwargs={'institution_id': '<pk>'},
    )

    users = RelationshipField(
        related_view='institutions:institution-users',
        related_view_kwargs={'institution_id': '<pk>'}
    )

    def get_api_url(self, obj):
        return obj.get_api_url()

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    class Meta:
        type_ = 'institutions'
