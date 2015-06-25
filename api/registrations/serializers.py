from rest_framework import serializers as ser

from rest_framework import exceptions
from framework.auth.core import Auth

from modularodm import Q
from website.project.model import MetaSchema
from api.nodes.serializers import NodeSerializer


class RegistrationSerializer(NodeSerializer):
    is_registration_draft = ser.BooleanField(read_only=True)


class RegistrationCreateSerializer(RegistrationSerializer):
    category = ser.CharField(read_only=True)
    title = ser.CharField(read_only=True)

    def create(self, validated_data):
        request = self.context['request']
        template = 'Open-Ended_Registration'
        schema = MetaSchema.find(
            Q('name', 'eq', template)).sort('-schema_version')[0]
        user = request.user
        node = self.context['view'].get_node()
        if node.is_registration is True:
            raise exceptions.ValidationError('This is already a registration')
        registration = node.register_node(
            schema=schema,
            auth=Auth(user),
            template=template,
            data=None
        )
        registration.is_registration_draft = False
        registration.save()
        return registration