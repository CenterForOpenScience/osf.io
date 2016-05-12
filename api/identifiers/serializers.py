from rest_framework import serializers as ser
from api.base.serializers import JSONAPISerializer, LinksField, RelationshipField
from api.base.utils import absolute_reverse


class IdentifierSerializer(JSONAPISerializer):

    category = ser.CharField(read_only=True)
    identifier = ser.CharField(read_only=True)

    identifier = LinksField({
        'self': 'get_absolute_url'
    })

    node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<pk>'},
        always_embed=True

    )

    class Meta:
        type_ = 'identifiers'

    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'nodes:node-identifier-detail',
            kwargs={
                'node_id': node_id,
                'user_id': obj._id
            }
        )
