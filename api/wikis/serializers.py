from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, IDField, TypeField, LinksField, RelationshipField


class WikiSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(source='page_name')
    # path
    materialized = ser.CharField(source='page_name')
    version = ser.IntegerField()
    date_modified = ser.DateTimeField(source='date')
    is_current = ser.BooleanField()
    content = ser.CharField()
    user = RelationshipField(related_view='users:user-detail', related_view_kwargs={'user_id': '<user._id>'})
    node = RelationshipField(related_view='nodes:node-detail', related_view_kwargs={'node_id': '<node._id>'})

    # LinksField.to_representation adds link to "self"
    links = LinksField({})

    class Meta:
        type_ = 'wikis'


class WikiDetailSerializer(WikiSerializer):
    """
    Overrides Wiki Serializer to make id required.
    """
    id = IDField(source='_id', required=True)
