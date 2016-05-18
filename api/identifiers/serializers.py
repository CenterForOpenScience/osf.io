from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField


class IdentifierSerializer(JSONAPISerializer):

    category = ser.CharField(read_only=True)

    identifier = LinksField({
        'self': 'get_identifiers'
    })

    referent = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<referent._id>'},
    )

    class Meta:
        type_ = 'identifiers'

    def get_identifiers(self, obj):
        return obj.value

    def get_absolute_url(self, obj):
        return obj.absolute_api_v2_url
