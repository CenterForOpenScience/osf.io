from rest_framework import serializers as ser

from api.base.serializers import LinkedSerializer
from website.models import Node
from framework.auth.core import Auth

class NodeSerializer(LinkedSerializer):

    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(required=True)
    description = ser.CharField(required=False, allow_blank=True)
    is_public = ser.BooleanField()

    def get_links(self, obj):
        return {
            'html': obj.absolute_url,
        }

    def create(self, validated_data):
        node = Node(**validated_data)
        node.save()
        return node

    def update(self, instance, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        if not isinstance(instance, Node):
            raise ValueError('instance must be a Node.')
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
