from framework.auth.core import Auth
from rest_framework import exceptions
from rest_framework import serializers as ser
from django.utils.translation import ugettext_lazy as _

from modularodm import Q
from api.base.utils import token_creator
from website.project.model import MetaSchema
from api.nodes.serializers import NodeSerializer


class RegistrationSerializer(NodeSerializer):
    is_registration_draft = ser.BooleanField(read_only=True)


class RegistrationCreateSerializer(RegistrationSerializer):
    category = ser.CharField(read_only=True)
    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)


class RegistrationCreateSerializerWithToken(RegistrationSerializer):
    category = ser.CharField(read_only=True)
    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)

    def validate(self, data):
        request = self.context['request']
        user = request.user
        view = self.context['view']
        node = view.get_node()
        given_token = view.kwargs['token']
        correct_token = token_creator(node._id, user._id)
        if node.is_registration_draft is False:
            raise exceptions.ValidationError(_('This is not a registration draft.'))
        if correct_token != given_token:
            raise ser.ValidationError("Incorrect token.")
        return data

    def create(self, validated_data):
        request = self.context['request']
        template = 'Open-Ended_Registration'
        schema = MetaSchema.find(
            Q('name', 'eq', template)).sort('-schema_version')[0]
        user = request.user
        node = self.context['view'].get_node()
        registration = node.register_node(
            schema=schema,
            auth=Auth(user),
            template=template,
            data=None
        )
        registration.is_registration_draft = False
        registration.is_deleted = False
        registration.save()
        return registration
