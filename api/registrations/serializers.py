from rest_framework import serializers as ser

from rest_framework import exceptions
from framework.auth.core import Auth

from modularodm import Q
from website.language import REGISTER_WARNING
from website.project.model import MetaSchema
from api.nodes.serializers import NodeSerializer
from api.base.utils import token_creator, absolute_reverse
from api.base.exceptions import Accepted

class RegistrationSerializer(NodeSerializer):
    is_registration_draft = ser.BooleanField(read_only=True)


class RegistrationCreateSerializer(RegistrationSerializer):
    category = ser.CharField(read_only=True)
    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)

    def validate(self, data):
        request = self.context['request']
        user = request.user
        node = self.context['view'].get_node()
        token = token_creator(node._id, user._id, data)
        url = absolute_reverse('registrations:registration-create', kwargs={'registration_id': node._id, 'token': token})
        registration_warning = REGISTER_WARNING.format((node.title))
        raise Accepted({'data':{'id': node._id, 'warning_message': registration_warning}, 'links': {'confirm_delete': url }})

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
        correct_token = token_creator(node._id, user._id, data)
        if correct_token != given_token:
            raise ser.ValidationError("Incorrect token.")
        if node.is_registration is True:
            raise exceptions.ValidationError('This is already a registration')
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