from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link, WaterbutlerLink
from website.models import Node
from framework.auth.core import Auth


class NodeSerializer(JSONAPISerializer):

    filterable_fields = frozenset(['title', 'description'])

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True)
    category = ser.ChoiceField(choices=Node.CATEGORY_MAP.keys())
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)
    tags = ser.SerializerMethodField()

    links = LinksField({
        'html': 'get_absolute_url',
        'children': {
            'related': Link('nodes:node-children', kwargs={'pk': '<pk>'}),
            'count': 'get_node_count'
        },
        'contributors': {
            'related': Link('nodes:node-contributors', kwargs={'pk': '<pk>'}),
            'count': 'get_contrib_count'
        },
        'pointers': {
            'related': Link('nodes:node-pointers', kwargs={'pk': '<pk>'})
        },
        'registrations': {
            'related': Link('nodes:node-registrations', kwargs={'pk': '<pk>'}),
            'count': 'get_registration_count'
        },
        'files': {
            'related': Link('nodes:node-files', kwargs={'pk': '<pk>'})
        },
    })
    properties = ser.SerializerMethodField()
    public = ser.BooleanField(source='is_public')
    # TODO: finish me

    class Meta:
        type_ = 'nodes'

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def get_node_count(self, obj):
        return len(obj.nodes)

    def get_contrib_count(self, obj):
        return len(obj.contributors)

    def get_registration_count(self, obj):
        return len(obj.node__registrations)

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
        is_public = validated_data.pop('is_public')
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        request = self.context['request']
        user = request.user
        auth = Auth(user)
        if is_public != instance.is_public:
            privacy = 'public' if is_public else 'private'
            instance.set_privacy(privacy, auth)
        instance.save()
        return instance


class NodePointersSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    node_id = ser.CharField(source='node._id')
    title = ser.CharField(read_only=True, source='node.title')

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
        pointer = node.add_pointer(pointer_node, auth, save=True)
        return pointer


class NodeFilesSerializer(JSONAPISerializer):

    id = ser.CharField(read_only=True, source='_id')
    provider = ser.CharField(read_only=True)
    path = ser.CharField(read_only=True)
    item_type = ser.CharField(read_only=True)
    name = ser.CharField(read_only=True)
    valid_self_link_methods = ser.ListField(read_only=True)
    metadata = ser.DictField(read_only=True)

    class Meta:
        type_ = 'files'

    links = LinksField({
        'self': WaterbutlerLink(kwargs={'node_id': '<node_id>'}),
        'related': Link('nodes:node-files', kwargs={'pk': '<node_id>'},
                        query_kwargs={'path': '<path>', 'provider': '<provider>'}),
    })

    def create(self, validated_data):
        # TODO
        pass

    def update(self, instance, validated_data):
        # TODO
        pass
