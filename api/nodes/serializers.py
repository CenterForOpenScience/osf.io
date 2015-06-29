from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from rest_framework import serializers as ser

from api.users.serializers import UserSerializer
from website.models import Node, User
from framework.auth.core import Auth
from api.base.serializers import JSONAPISerializer, LinksField, Link, WaterbutlerLink


class NodeSerializer(JSONAPISerializer):
    # TODO: If we have to redo this implementation in any of the other serializers, subclass ChoiceField and make it
    # handle blank choices properly. Currently DRF ChoiceFields ignore blank options, which is incorrect in this
    # instance
    category_choices = Node.CATEGORY_MAP.keys()
    category_choices_string = ', '.join(["'{}'".format(choice) for choice in category_choices])
    filterable_fields = frozenset(['title', 'description', 'public'])

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    category = ser.ChoiceField(choices=category_choices, help_text="Choices: " + category_choices_string)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    tags = ser.SerializerMethodField(help_text='A dictionary that contains two lists of tags: '
                                               'user and system. Any tag that a user will define in the UI will be '
                                               'a user tag')

    links = LinksField({
        'html': 'get_absolute_url',
        'children': {
            'related': Link('nodes:node-children', kwargs={'node_id': '<pk>'}),
            'count': 'get_node_count',
        },
        'contributors': {
            'related': Link('nodes:node-contributors', kwargs={'node_id': '<pk>'}),
            'count': 'get_contrib_count',
        },
        'pointers': {
            'related': Link('nodes:node-pointers', kwargs={'node_id': '<pk>'}),
            'count': 'get_pointers_count',
        },
        'registrations': {
            'related': Link('nodes:node-registrations', kwargs={'node_id': '<pk>'}),
            'count': 'get_registration_count',
        },
        'files': {
            'related': Link('nodes:node-files', kwargs={'node_id': '<pk>'})
        },
    })
    properties = ser.SerializerMethodField(help_text='A dictionary of read-only booleans: registration, collection,'
                                                     'and dashboard. Collections are special nodes used by the Project '
                                                     'Organizer to, as you would imagine, organize projects. '
                                                     'A dashboard is a collection node that serves as the root of '
                                                     'Project Organizer collections. Every user will always have '
                                                     'one Dashboard')
    # TODO: When we have 'admin' permissions, make this writable for admins
    public = ser.BooleanField(source='is_public', read_only=True,
                              help_text='Nodes that are made public will give read-only access '
                                                            'to everyone. Private nodes require explicit read '
                                                            'permission. Write and admin access are the same for '
                                                            'public and private nodes. Administrators on a parent '
                                                            'node have implicit read permissions for all child nodes',
                              )
    # TODO: finish me

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
        nodes = [node for node in obj.nodes if node.can_view(auth) and node.primary]
        return len(nodes)

    def get_contrib_count(self, obj):
        return len(obj.contributors)

    def get_registration_count(self, obj):
        auth = self.get_user_auth(self.context['request'])
        registrations = [node for node in obj.node__registrations if node.can_view(auth)]
        return len(registrations)

    def get_pointers_count(self, obj):
        return len(obj.nodes_pointer)

    @staticmethod
    def get_properties(obj):
        ret = {
            'registration': obj.is_registration,
            'collection': obj.is_folder,
            'dashboard': obj.is_dashboard,
        }
        return ret

    @staticmethod
    def get_tags(obj):
        ret = {
            'system': [tag._id for tag in obj.system_tags],
            'user': [tag._id for tag in obj.tags],
        }
        return ret

    def create(self, validated_data):
        node = Node(**validated_data)
        node.save()
        return node

    def update(self, instance, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(instance, Node), 'instance must be a Node'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class NodePointersSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    node_id = ser.CharField(source='node._id', help_text='The ID of the node that this pointer points to')
    title = ser.CharField(read_only=True, source='node.title', help_text='The title of the node that this pointer '
                                                                         'points to')

    class Meta:
        type_ = 'pointers'

    links = LinksField({
        'html': 'get_absolute_url',
    })

    def get_absolute_url(self, obj):
        pointer_node = Node.load(obj.node._id)
        return pointer_node.absolute_url

    def create(self, validated_data):
        request = self.context['request']
        user = request.user
        auth = Auth(user)
        node = self.context['view'].get_node()
        pointer_node = Node.load(validated_data['node']['_id'])
        if not pointer_node:
            raise NotFound('Node not found.')
        try:
            pointer = node.add_pointer(pointer_node, auth, save=True)
            return pointer
        except ValueError:
            raise ValidationError('Pointer to node {} already in list'.format(pointer_node._id))

    def update(self, instance, validated_data):
        pass

class NodeFilesSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    provider = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    item_type = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)
    metadata = ser.DictField(read_only=True)

    class Meta:
        type_ = 'files'

    links = LinksField({
        'self': WaterbutlerLink(kwargs={'node_id': '<node_id>'}),
        'self_methods': 'valid_self_link_methods',
        'related': Link('nodes:node-files', kwargs={'node_id': '<node_id>'},
                        query_kwargs={'path': '<path>', 'provider': '<provider>'}),
    })

    @staticmethod
    def valid_self_link_methods(obj):
        return obj['valid_self_link_methods']

    def create(self, validated_data):
        # TODO
        pass

    def update(self, instance, validated_data):
        # TODO
        pass


class ContributorSerializer(UserSerializer):

    admin = ser.BooleanField(read_only=True, help_text='Whether the user will be able to add and remove contributors')
    id = ser.CharField(source='_id')
    fullname = ser.CharField(read_only=True, help_text='Display name used in the general user interface')
    given_name = ser.CharField(read_only=True, help_text='For bibliographic citations')
    middle_name = ser.CharField(read_only=True, source='middle_names', help_text='For bibliographic citations')
    family_name = ser.CharField(read_only=True, help_text='For bibliographic citations')
    suffix = ser.CharField(read_only=True, help_text='For bibliographic citations')
    date_registered = ser.DateTimeField(read_only=True)
    gravatar_url = ser.CharField(read_only=True, help_text='URL for the icon used to identify the user. Relies on http://gravatar.com ')
    employment_institutions = ser.ListField(read_only=True, source='jobs', help_text='An array of dictionaries representing the '
                                                                     'places the user has worked')
    educational_institutions = ser.ListField(read_only=True, source='schools', help_text='An array of dictionaries representing the '
                                                                         'places the user has attended school')
    social_accounts = ser.DictField(read_only=True, source='social', help_text='A dictionary of various social media account '
                                                     'identifiers including an array of user-defined URLs')
    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'user_id': '<_id>'})
        },
        'edit contributor': Link('nodes:node-contributor-detail', kwargs={'user_id': '<_id>', 'node_id': '<node_id>'})
    })

    def absolute_url(self, obj):
        return obj.absolute_url

    def create(self, validated_data):
        user = self.context['request'].user
        auth = Auth(user)
        node = self.context['view'].get_node()
        contributor = User.load(validated_data['_id'])
        if not contributor:
            raise NotFound('User with id {} cannot be found.'.format(validated_data['_id']))
        elif contributor in node.contributors:
            raise ValidationError('User {} already is a contributor'.format(contributor.username))
        permissions = ['read', 'write']
        node.add_contributor(contributor=contributor, auth=auth, permissions=permissions, save=True)
        contributor.node_id = node._id
        return contributor


class ContributorDetailSerializer(ContributorSerializer):

    id = ser.CharField(source='_id', read_only=True)
    admin = ser.BooleanField(help_text='Whether the user will be able to add and remove contributors')
    local_filterable = frozenset(['admin'])
    filterable_fields = frozenset.union(UserSerializer.filterable_fields, local_filterable)
    bibliographic = ser.BooleanField(help_text='Whether the user will be included in citations for this node or not')

    def update(self, user, validated_data):
        node = self.context['view'].get_node()
        bibliographic = (validated_data['bibliographic'] == "True")
        if bibliographic != node.get_visible(user):
            node.set_visible(user, bibliographic, save=True)
        admin_field = (validated_data['admin'] == "True")
        if admin_field == node.has_permission(user, 'admin'):
            pass
        elif admin_field:
            node.add_permission(user, 'admin', save=True)
        elif len(node.admin_contributor_ids) > 1:
            node.remove_permission(user, 'admin', save=True)
        else:
            raise PermissionDenied('Admin privileges for {} cannot be removed as they are the only admin.'.format(user.username))
        return self.context['view'].get_object()

    def destroy(self, user, validated_data):
        auth = Auth(user)
        node = self.context['view'].get_node()
        contributor = self.get_object()
        node.rm_contributor(contributor, auth)
        node.save()

    links = LinksField({
        'html': 'absolute_url',
        'nodes': {
            'relation': Link('users:user-nodes', kwargs={'user_id': '<_id>'})},
    })
