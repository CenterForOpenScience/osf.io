from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.serializers import JSONAPISerializer
from api.nodes.serializers import NodeSerializer
from api.base.serializers import IDField, JSONAPIHyperlinkedIdentityField


class RegistrationSerializer(NodeSerializer):

    id = IDField(source='_id', read_only=True)
    registration = ser.BooleanField(read_only=True, source='is_registration')
    retracted = ser.BooleanField(source='is_retracted', read_only=True,
        help_text='Whether this registration has been retracted.')
    registered_date = ser.DateTimeField(read_only=True)

    # registered_from = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-detail', lookup_field='pk', link_type='related',
    #                                           lookup_url_kwarg='registered_from')
    # registered_user = JSONAPIHyperlinkedIdentityField(view_name='nodes:node-detail', lookup_field='pk', link_type='related',
    #                                           lookup_url_kwarg='node_id')


    # TODO: Finish me

    # TODO: Override create?

    def update(self, *args, **kwargs):
        raise exceptions.ValidationError('Registrations cannot be modified.')


class RegistrationDetailSerializer(NodeSerializer):
    """
    Overrides NodeSerializer to make id required.
    """
    id = IDField(source='_id', required=True)


    # registration_choices = ['immediate', 'embargo']
    #
    # draft_id = ser.CharField(write_only=True)
    # registration_choice = ser.ChoiceField(write_only=True, choices=registration_choices, help_text='Choose whether '
    #                     'to make your registration public immediately or embargo it for up to four years.')
    # embargo_end_date = ser.DateField(write_only=True, required=False)
    # id = ser.CharField(read_only=True, source='_id')
    # title = ser.CharField(read_only=True)
    # description = ser.CharField(read_only=True)
    # category = ser.CharField(read_only=True)