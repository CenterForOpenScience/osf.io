from framework.auth.core import Auth
from rest_framework import serializers as ser

from api.base.utils import token_creator
from api.nodes.serializers import NodeSerializer
from api.base.serializers import JSONAPISerializer
from api.draft_registrations.views import DraftRegistrationMixin
from api.base.utils import get_object_or_404
from website.project.model import DraftRegistration, Node


class RegistrationCreateSerializer(JSONAPISerializer):
    id = ser.CharField(read_only=True, source='_id')
    class Meta:
        type_='registrations'

class RegistrationCreateSerializerWithToken(NodeSerializer, DraftRegistrationMixin):
    id = ser.CharField(read_only=True, source='_id')
    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category = ser.CharField(read_only=True)

    def validate(self, data):
        request = self.context['request']
        user = request.user
        view = self.context['view']
        draft = get_object_or_404(DraftRegistration, view.kwargs['registration_id'])
        given_token = view.kwargs['token']
        correct_token = token_creator(draft._id, user._id)
        if correct_token != given_token:
            raise ser.ValidationError("Incorrect token.")
        return data

    def create(self, validated_data):
        request = self.context['request']
        view = self.context['view']
        draft = get_object_or_404(DraftRegistration, view.kwargs['registration_id'])
        node = draft.branched_from
        schema = draft.registration_schema
        data = draft.registration_metadata
        user = request.user
        registration = node.register_node(
            schema=schema,
            auth=Auth(user),
            template=schema.schema['title'],
            data=data
        )
        registration.is_deleted = False
        registration.registered_from = get_object_or_404(Node, node._id)
        registration.save()
        return registration
