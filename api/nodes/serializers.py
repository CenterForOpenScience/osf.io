from rest_framework import serializers as ser
from rest_framework import exceptions
from modularodm.exceptions import ValidationValueError

from framework.auth.core import Auth
from framework.exceptions import PermissionsError

from website.models import Node, User
from website.exceptions import NodeStateError
from website.util import permissions as osf_permissions

from api.base.utils import get_object_or_error, absolute_reverse, add_dev_only_items
from api.base.serializers import (JSONAPISerializer, WaterbutlerLink, NodeFileHyperLink, IDField, TypeField,
    TargetTypeField, JSONAPIListField, LinksField, JSONAPIHyperlinkedIdentityField, DevOnly)
from api.base.exceptions import InvalidModelValueError


class NodeTagField(ser.Field):
    def to_representation(self, obj):
        if obj is not None:
            return obj._id
        return None

    def to_internal_value(self, data):
        return data


class NodeSerializer(JSONAPISerializer):
    # TODO: If we have to redo this implementation in any of the other serializers, subclass ChoiceField and make it
    # handle blank choices properly. Currently DRF ChoiceFields ignore blank options, which is incorrect in this
    # instance
    filterable_fields = frozenset([
        'title',
        'description',
        'public',
        'tags',
        'category',
        'date_created',
        'date_modified'
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    category_choices = Node.CATEGORY_MAP.keys()
    category_choices_string = ', '.join(["'{}'".format(choice) for choice in category_choices])

    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    category = ser.ChoiceField(choices=category_choices, help_text="Choices: " + category_choices_string)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    registration = ser.BooleanField(read_only=True, source='is_registration')
    fork = ser.BooleanField(read_only=True, source='is_fork')
    collection = DevOnly(ser.BooleanField(read_only=True, source='is_folder'))
    dashboard = ser.BooleanField(read_only=True, source='is_dashboard')
    tags = JSONAPIListField(child=NodeTagField(), required=False)

    # Public is only write-able by admins--see update method
    public = ser.BooleanField(source='is_public', required=False,
                              help_text='Nodes that are made public will give read-only access '
                                        'to everyone. Private nodes require explicit read '
                                        'permission. Write and admin access are the same for '
                                        'public and private nodes. Administrators on a parent '
                                        'node have implicit read permissions for all child nodes',
                              )

    links = LinksField({'html': 'get_absolute_url'})
    # TODO: When we have osf_permissions.ADMIN permissions, make this writable for admins

    children = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-children', lookup_field='pk', link_type='related',
                                                lookup_url_kwarg='node_id', meta={'count': 'get_node_count'})

    contributors = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-contributors', lookup_field='pk', link_type='related',
                                                    lookup_url_kwarg='node_id', meta={'count': 'get_contrib_count'})

    files = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-providers', lookup_field='pk', lookup_url_kwarg='node_id',
                                             link_type='related')

    node_links = DevOnly(JSONAPIHyperlinkedIdentityField(view_name='nodes:node-pointers', lookup_field='pk', link_type='related',
                                                  lookup_url_kwarg='node_id', meta={'count': 'get_pointers_count'}))

    parent = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-detail', lookup_field='parent_id', link_type='related',
                                              lookup_url_kwarg='node_id')

    registrations = DevOnly(JSONAPIHyperlinkedIdentityField(view_name='nodes:node-registrations', lookup_field='pk', link_type='related',
                                                     lookup_url_kwarg='node_id', meta={'count': 'get_registration_count'}))

    forked_from = JSONAPIHyperlinkedIdentityField(
        view_name='nodes:node-detail',
        lookup_field='forked_from_id',
        link_type='related',
        lookup_url_kwarg='node_id'
    )

    class Meta:
        type_ = 'nodes'

    def get_absolute_url(self, obj):
        return obj.absolute_url

    # TODO: See if we can get the count filters into the filter rather than the serializer.

    def get_user_auth(self, request):
        user = request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        return auth

    def get_node_count(self, obj):
        auth = self.get_user_auth(self.context['request'])
        nodes = [node for node in obj.nodes if node.can_view(auth) and node.primary and not node.is_deleted]
        return len(nodes)

    def get_contrib_count(self, obj):
        return len(obj.contributors)

    def get_registration_count(self, obj):
        auth = self.get_user_auth(self.context['request'])
        registrations = [node for node in obj.node__registrations if node.can_view(auth)]
        return len(registrations)

    def get_pointers_count(self, obj):
        return len(obj.nodes_pointer)

    def create(self, validated_data):
        node = Node(**validated_data)
        try:
            node.save()
        except ValidationValueError as e:
            raise InvalidModelValueError(detail=e.message)
        return node

    def update(self, node, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(node, Node), 'node must be a Node'
        auth = self.get_user_auth(self.context['request'])
        tags = validated_data.get('tags')
        if tags is not None:
            del validated_data['tags']
            current_tags = set(tags)
        else:
            current_tags = set()
        old_tags = set([tag._id for tag in node.tags])
        for new_tag in (current_tags - old_tags):
            node.add_tag(new_tag, auth=auth)
        for deleted_tag in (old_tags - current_tags):
            node.remove_tag(deleted_tag, auth=auth)

        if validated_data:
            try:
                node.update(validated_data, auth=auth)
            except ValidationValueError as e:
                raise InvalidModelValueError(detail=e.message)
            except PermissionsError:
                raise exceptions.PermissionDenied

        return node


class NodeDetailSerializer(NodeSerializer):
    """
    Overrides NodeSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


class NodeContributorsSerializer(JSONAPISerializer):
    """ Separate from UserSerializer due to necessity to override almost every field as read only
    """
    filterable_fields = frozenset([
        'id',
        'bibliographic',
        'permission'
    ])

    id = IDField(source='_id', required=True)
    type = TypeField()

    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not.',
                                     default=True)
    permission = ser.ChoiceField(choices=osf_permissions.PERMISSIONS, required=False, allow_null=True,
                                 default=osf_permissions.reduce_permissions(osf_permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS),
                                 help_text='User permission level. Must be "read", "write", or "admin". Defaults to "write".')

    links = LinksField(add_dev_only_items({
        'html': 'absolute_url',
        'self': 'get_absolute_url'
    }, {
        'profile_image': 'profile_image_url',
    }))
    users = JSONAPIHyperlinkedIdentityField(view_name='users:user-detail', lookup_field='pk', lookup_url_kwarg='user_id',
                                             link_type='related')

    def profile_image_url(self, user):
        size = self.context['request'].query_params.get('profile_image_size')
        return user.profile_image_url(size=size)

    class Meta:
        type_ = 'contributors'

    def absolute_url(self, obj):
        return obj.absolute_url

    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'nodes:node-contributor-detail',
            kwargs={
                'node_id': node_id,
                'user_id': obj._id
            }
        )


class NodeContributorsCreateSerializer(NodeContributorsSerializer):
    """
    Overrides NodeContributorsSerializer to add target_type field
    """
    target_type = TargetTypeField(target_type='users')

    def create(self, validated_data):
        auth = Auth(self.context['request'].user)
        node = self.context['view'].get_node()
        contributor = get_object_or_error(User, validated_data['_id'], display_name='user')
        # Node object checks for contributor existence but can still change permissions anyway
        if contributor in node.contributors:
            raise exceptions.ValidationError('{} is already a contributor'.format(contributor.fullname))

        bibliographic = validated_data['bibliographic']
        permissions = osf_permissions.expand_permissions(validated_data.get('permission')) or osf_permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS
        node.add_contributor(contributor=contributor, auth=auth, visible=bibliographic, permissions=permissions, save=True)
        contributor.permission = osf_permissions.reduce_permissions(node.get_permissions(contributor))
        contributor.bibliographic = node.get_visible(contributor)
        contributor.node_id = node._id
        return contributor


class NodeContributorDetailSerializer(NodeContributorsSerializer):
    """
    Overrides node contributor serializer to add additional methods
    """

    def update(self, instance, validated_data):
        contributor = instance
        auth = Auth(self.context['request'].user)
        node = self.context['view'].get_node()

        visible = validated_data.get('bibliographic')
        permission = validated_data.get('permission')
        try:
            node.update_contributor(contributor, permission, visible, auth, save=True)
        except NodeStateError as e:
            raise exceptions.ValidationError(e)
        contributor.permission = osf_permissions.reduce_permissions(node.get_permissions(contributor))
        contributor.bibliographic = node.get_visible(contributor)
        contributor.node_id = node._id
        return contributor


class NodeLinksSerializer(JSONAPISerializer):

    id = IDField(source='_id')
    type = TypeField()
    target_type = TargetTypeField(target_type='nodes')

    # TODO: We don't show the title because the current user may not have access to this node. We may want to conditionally
    # include this field in the future.
    # title = ser.CharField(read_only=True, source='node.title', help_text='The title of the node that this Node Link '
    #                                                                      'points to')

    target_node = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-detail', lookup_field='pk', link_type='related',
                                              lookup_url_kwarg='node_id')
    class Meta:
        type_ = 'node_links'

    links = LinksField({
        'self': 'get_absolute_url'
    })

    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'nodes:node-pointer-detail',
            kwargs={
                'node_id': node_id,
                'node_link_id': obj._id
            }
        )

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        auth = Auth(user)
        node = self.context['view'].get_node()
        pointer_node = Node.load(validated_data['_id'])
        if not pointer_node:
            raise exceptions.NotFound('Node not found.')
        try:
            pointer = node.add_pointer(pointer_node, auth, save=True)
            return pointer
        except ValueError:
            raise exceptions.ValidationError('Node link to node {} already in list'.format(pointer_node._id))

    def update(self, instance, validated_data):
        pass


class NodeProviderSerializer(JSONAPISerializer):

    id = ser.SerializerMethodField(read_only=True)
    kind = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    node = ser.CharField(source='node_id', read_only=True)
    provider = ser.CharField(read_only=True)
    files = NodeFileHyperLink(kind='folder', read_only=True, link_type='related', view_name='nodes:node-files', kwargs=('node_id', 'path', 'provider'))
    links = LinksField({
        'upload': WaterbutlerLink(),
        'new_folder': WaterbutlerLink(kind='folder')
    })

    class Meta:
        type_ = 'files'

    @staticmethod
    def get_id(obj):
        return '{}:{}'.format(obj.node._id, obj.provider)
