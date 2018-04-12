import sys

from addons.wiki.models import WikiPage, WikiVersion
from rest_framework import serializers as ser
from rest_framework.exceptions import ValidationError, MethodNotAllowed, NotFound

from api.base.exceptions import Conflict
from addons.wiki.exceptions import (
    NameInvalidError,
    NameMaximumLengthError,
    PageConflictError,
    WikiError,
)
from api.base.serializers import (
    JSONAPISerializer,
    IDField,
    TypeField,
    Link,
    LinksField,
    RelationshipField,
    VersionedDateTimeField,
)
from api.base.utils import absolute_reverse

from framework.auth.core import Auth


class WikiSerializer(JSONAPISerializer):

    filterable_fields = frozenset([
        'name',
        'date_modified'
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()
    name = ser.CharField(source='page_name', allow_blank=False)
    kind = ser.SerializerMethodField()
    size = ser.SerializerMethodField()
    path = ser.SerializerMethodField()
    content = ser.CharField(write_only=True, required=False, allow_blank=False)
    materialized_path = ser.SerializerMethodField(method_name='get_path')
    date_modified = VersionedDateTimeField(source='modified', read_only=True)
    content_type = ser.SerializerMethodField()
    current_user_can_comment = ser.SerializerMethodField(help_text='Whether the current user is allowed to post comments')
    extra = ser.SerializerMethodField(help_text='Additional metadata about this wiki')

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'}
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
        return '/{}'.format(obj._id)

    def get_kind(self, obj):
        return 'file'

    def get_size(self, obj):
        return sys.getsizeof(obj.get_version().content)

    def get_current_user_can_comment(self, obj):
        user = self.context['request'].user
        auth = Auth(user if not user.is_anonymous else None)
        return obj.node.can_comment(auth)

    def get_content_type(self, obj):
        return 'text/markdown'

    def get_extra(self, obj):
        return {
            'version': obj.get_version().identifier
        }

    def get_wiki_content(self, obj):
        return absolute_reverse('wikis:wiki-content', kwargs={
            'wiki_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })


class NodeWikiSerializer(WikiSerializer):
    node = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<node._id>'}
    )

    comments = RelationshipField(
        related_view='nodes:node-comments',
        related_view_kwargs={'node_id': '<node._id>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': '<_id>'}
    )

    versions = RelationshipField(
        related_view='wikis:wiki-versions',
        related_view_kwargs={'wiki_id': '<_id>'},
    )

    def update(self, instance, validated_data):
        auth = Auth(self.context['request'].user)
        new_page_name = validated_data.get('page_name')
        validated_data.pop('content', None)

        try:
            instance = instance.node.rename_node_wiki(instance.page_name, new_page_name, auth)
        except PageConflictError as err:
            raise Conflict(err.args[0])
        except WikiError as err:
            if err.args:
                raise ValidationError(err.args[0])
            raise ValidationError
        return instance

    def create(self, validated_data):
        auth = Auth(self.context['request'].user)
        node = validated_data.get('node')
        name = validated_data.get('page_name')
        content = validated_data.get('content', '')

        if node.addons_wiki_node_settings.deleted:
            raise NotFound(detail='The wiki for this node has been disabled.')

        if WikiPage.objects.get_for_node(node, name):
            raise Conflict("A wiki page with the name '{}' already exists.".format(name))

        try:
            wiki_page, _ = node.update_node_wiki(name=name, content=content, auth=auth)
        except (
            NameInvalidError, NameMaximumLengthError
        ) as err:
            raise ValidationError(err.args[0])

        return wiki_page


class RegistrationWikiSerializer(WikiSerializer):

    node = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<node._id>'}
    )

    comments = RelationshipField(
        related_view='registrations:registration-comments',
        related_view_kwargs={'node_id': '<node._id>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': '<_id>'}
    )

    def create(self, validated_data):
        raise MethodNotAllowed(method=self.context['request'].method)


class NodeWikiDetailSerializer(NodeWikiSerializer):
    """
    Overrides NodeWikiSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class RegistrationWikiDetailSerializer(RegistrationWikiSerializer):
    """
    Overrides NodeWikiSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class WikiVersionSerializer(JSONAPISerializer):
    id = ser.CharField(read_only=True, source='identifier')
    type = TypeField()
    size = ser.SerializerMethodField()
    content_type = ser.SerializerMethodField()
    date_created = VersionedDateTimeField(source='created', read_only=True, help_text='The date that this version was created')

    wiki_page = RelationshipField(
        related_view='wikis:wiki-detail',
        related_view_kwargs={'wiki_id': '<wiki_page._id>'}
    )

    user = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'}
    )

    links = LinksField({
        'self': 'self_url',
        'download': 'get_wiki_content'
    })

    def self_url(self, obj):
        return absolute_reverse('wikis:wiki-version-detail', kwargs={
            'version_id': obj.identifier,
            'wiki_id': obj.wiki_page._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_content_type(self, obj):
        return 'text/markdown'

    def get_size(self, obj):
        # The size of this wiki at this version
        return sys.getsizeof(obj.content)

    def get_wiki_content(self, obj):
        return absolute_reverse('wikis:wiki-version-content', kwargs={
            'version_id': obj.identifier,
            'wiki_id': obj.wiki_page._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    def create(self, validated_data):
        auth = Auth(self.context['request'].user)
        wiki_page = self.context['view'].get_wiki()
        content = validated_data.get('content', '')
        _, new_version = wiki_page.node.update_node_wiki(name=wiki_page.page_name, content=content, auth=auth)
        return new_version

    class Meta:
        type_ = 'wiki-versions'
