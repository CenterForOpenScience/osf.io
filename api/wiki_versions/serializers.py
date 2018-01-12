from rest_framework import serializers as ser

from api.base.serializers import (
    JSONAPISerializer,
    IDField,
    TypeField,
    LinksField,
    RelationshipField,
    DateByVersion,
)

from api.base.utils import absolute_reverse


class WikiVersionSerializer(JSONAPISerializer):
    id = IDField(source='_id', read_only=True)
    type = TypeField()
    identifier = ser.IntegerField()
    date_modified = DateByVersion(source='date')
    content_type = ser.SerializerMethodField()

    wiki_page = RelationshipField(
        related_view='wikis:wiki-detail',
        related_view_kwargs={'wiki_id': '<wiki_page._id>'}
    )

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'}
    )

    links = LinksField({
        'download': 'get_wiki_content'
    })

    def get_content_type(self, obj):
        return 'text/markdown'

    def get_wiki_content(self, obj):
        return absolute_reverse('wikis:wiki-content', kwargs={
            'wiki_id': obj.wiki_page._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    class Meta:
        type_ = 'wiki-version'
