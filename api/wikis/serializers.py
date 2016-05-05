from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, IDField, TypeField, Link, LinksField, RelationshipField
from api.base.utils import absolute_reverse


class WikiSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(source='page_name')
    path = ser.SerializerMethodField()
    materialized = ser.SerializerMethodField(method_name='get_path')
    date_modified = ser.DateTimeField(source='date')
    content_type = ser.SerializerMethodField()
    extra = ser.SerializerMethodField(read_only=True, help_text='Additional metadata about this wiki')

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'}
    )
    node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'}
    )
    comments = RelationshipField(
        related_view='nodes:node-comments',
        related_view_kwargs={'node_id': '<node._id>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': '<pk>'}
    )

    # LinksField.to_representation adds link to "self"
    links = LinksField({
        'info': Link('wikis:wiki-detail', kwargs={'wiki_id': '<_id>'}),
        'download': 'get_wiki_content'
    })

    class Meta:
        type_ = 'wikis'

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    def get_path(self, obj):
        return '/{}'.format(obj)

    def get_content_type(self, obj):
        return 'text/markdown'

    def get_extra(self, obj):
        return {
            'version': obj.version
        }

    def get_wiki_content(self, obj):
        return absolute_reverse('wikis:wiki-content', kwargs={
            'wiki_id': obj._id,
        })


class WikiDetailSerializer(WikiSerializer):
    """
    Overrides Wiki Serializer to make id required.
    """
    id = IDField(source='_id', required=True)
