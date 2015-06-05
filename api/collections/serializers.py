from rest_framework import serializers as ser

from api.base.serializers import JSONAPISerializer, LinksField, Link
from website.models import Node
from framework.auth.core import Auth


class CollectionSerializer(JSONAPISerializer):
    filterable_fields = frozenset(['title', 'is_dashboard'])

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(required=True)
    date_created = ser.DateTimeField(read_only=True)
    date_modified = ser.DateTimeField(read_only=True)

    links = LinksField({
        'html': 'get_absolute_url',
        'children': {
            'related': Link('collections:collection-children', kwargs={'pk': '<pk>'}),
            'count': 'get_node_count',
        },
        'parent': {
            'related': Link('collections:collection-parents', kwargs={'pk': '<pk>'}),
            'count': 'get_parents_count'
        },
        'pointers': {
            'related': Link('collections:collection-pointers', kwargs={'pk': '<pk>'}),
            'count': 'get_pointers_count',
        },
    })
    properties = ser.SerializerMethodField(help_text='A dictionary of read-only booleans: registration, collection,'
                                                     'and dashboard. Collections are special nodes used by the Project '
                                                     'Organizer to, as you would imagine, organize projects. '
                                                     'A dashboard is a collection node that serves as the root of '
                                                     'Project Organizer collections. Every user will always have '
                                                     'one Dashboard')
    # TODO: finish me

    class Meta:
        type_ = 'collections'

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

    def get_pointers_count(self, obj):
        return len(obj.nodes_pointer)

    def get_parents_count(self, obj):
        return len(obj.parents)

    @staticmethod
    def get_properties(obj):
        ret = {
            'collection': obj.is_folder,
            'dashboard': obj.is_dashboard,
        }
        return ret

    def create(self, validated_data):
        node = Node(**validated_data)
        node.save()
        node.is_folder = True
        return node

    def update(self, instance, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(instance, Node), 'instance must be a Node'
        if instance.is_dashboard:
            return instance
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class CollectionPointersSerializer(JSONAPISerializer):
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
        pointer = node.add_pointer(pointer_node, auth, save=True)
        return pointer

    def update(self, instance, validated_data):
        pass
