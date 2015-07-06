from framework.auth.core import Auth
from rest_framework import exceptions
from rest_framework import serializers as ser
from django.utils.translation import ugettext_lazy as _

from modularodm import Q
from api.base.utils import token_creator
from api.base.serializers import JSONAPISerializer
from website.project.model import MetaSchema, DraftRegistration
from website.project.metadata.schemas import OSF_META_SCHEMAS



class DraftRegSerializer(JSONAPISerializer):
    schema_choices = [schema['name'] for schema in OSF_META_SCHEMAS]
    id = ser.CharField(read_only=True, source='_id')
    branched_from = ser.CharField(read_only = True)
    initiator = ser.CharField(read_only=True)
    registration_schema = ser.CharField(read_only=True)
    registration_form = ser.ChoiceField(choices=schema_choices, required=True, write_only=True, help_text="Please select a registration form to initiate registration.")
    registration_metadata = ser.DictField(help_text="Responses to supplemental registration questions")
    schema_version = ser.IntegerField(help_text="Registration schema version", write_only=True)
    initiated = ser.DateTimeField(read_only=True)
    updated = ser.DateTimeField(read_only=True)
    completion = ser.CharField(read_only=True)

    class Meta:
        type_='draft-registrations'


    def update(self, instance, validated_data):
        """Update instance with the validated data. Requires
        the request to be in the serializer context.
        """
        assert isinstance(instance, DraftRegistration), 'instance must be a DraftRegistration'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class DraftRegistrationCreateSerializer(DraftRegSerializer):
    category = ser.CharField(read_only=True)
    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)


class DraftRegistrationCreateSerializerWithToken(DraftRegSerializer):
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

