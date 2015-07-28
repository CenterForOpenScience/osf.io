from rest_framework import serializers as ser

from website.models import Node
from framework.auth.core import Auth
from rest_framework import exceptions
from api.base.serializers import JSONAPISerializer, Link, WaterbutlerLink, Attribute, AttributeLinksField, \
    LinksFieldWIthSelfLink


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
    registration = ser.BooleanField(read_only=True, source='is_registration')
    collection = ser.BooleanField(read_only=True, source='is_folder')
    dashboard = ser.BooleanField(read_only=True, source='is_dashboard')

    links = LinksFieldWIthSelfLink({'html': 'get_absolute_url'})
    # TODO: When we have 'admin' permissions, make this writable for admins
    public = ser.BooleanField(source='is_public', read_only=True,
                              help_text='Nodes that are made public will give read-only access '
                                                            'to everyone. Private nodes require explicit read '
                                                            'permission. Write and admin access are the same for '
                                                            'public and private nodes. Administrators on a parent '
                                                            'node have implicit read permissions for all child nodes',
                              )

    relationships = AttributeLinksField({
        'children': {
            'links': {
                'related': {
                    'href': Link('nodes:node-children', kwargs={'node_id': '<pk>'}),
                    'meta': Attribute('children')
                }
            },
        },
        'contributors': {
            'links': {
                'related': {
                    'href': Link('nodes:node-contributors', kwargs={'node_id': '<pk>'}),
                    'meta': Attribute('contributors', 'contributors')
                }
            },
        },
        'pointers': {
            'links': {
                'related': {
                    'href': Link('nodes:node-pointers', kwargs={'node_id': '<pk>'}),
                    'meta': Attribute('pointers', 'nodes_pointer')
                }
            },
        },
        'registrations': {
            'links': {
                'related': {
                    'href': Link('nodes:node-registrations', kwargs={'node_id': '<pk>'}),
                    'meta': Attribute('registrations')
                }
            },
        },
    })

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

    links = LinksFieldWIthSelfLink({
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
            raise exceptions.NotFound('Node not found.')
        try:
            pointer = node.add_pointer(pointer_node, auth, save=True)
            return pointer
        except ValueError:
            raise exceptions.ValidationError('Pointer to node {} already in list'.format(pointer_node._id))

    def update(self, instance, validated_data):
        pass


class NodeFilesSerializer(JSONAPISerializer):
    id = ser.SerializerMethodField()
    provider = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    item_type = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)
    content_type = ser.CharField(read_only=True)
    modified = ser.DateTimeField(read_only=True)
    size = ser.CharField(read_only=True)
    extra = ser.DictField(read_only=True)

    class Meta:
        type_ = 'files'

    links = LinksFieldWIthSelfLink({
        'self': WaterbutlerLink(kwargs={'node_id': '<node_id>'}),
        'related': {
            'href': Link('nodes:node-files', kwargs={'node_id': '<node_id>'},
                        query_kwargs={'path': '<path>', 'provider': '<provider>'}),
            'meta': {
                'self_methods': 'valid_self_link_methods'
            }
        }
    })

    @staticmethod
    def get_id(obj):
        ret = obj['provider'] + obj['path']
        return ret

    @staticmethod
    def valid_self_link_methods(obj):
        return obj['valid_self_link_methods']

    def create(self, validated_data):
        # TODO
        pass

    def update(self, instance, validated_data):
        # TODO
        pass
