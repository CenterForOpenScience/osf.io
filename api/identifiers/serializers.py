from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField, IDField


class IdentifierSerializer(JSONAPISerializer):

    category = ser.CharField(read_only=True)

    filterable_fields = frozenset(['category'])

    value = ser.CharField(read_only=True)

    referent = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<referent._id>'},
    )

    id = IDField(source='_id', read_only=True)

    class Meta:
        type_ = 'identifiers'

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url

    def get_id(self, obj):
        return obj._id
