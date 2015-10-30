from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeSerializer
from api.base.serializers import IDField, JSONAPIHyperlinkedIdentityField, LinksField


class RegistrationSerializer(NodeSerializer):

    retracted = ser.BooleanField(source='is_retracted', read_only=True,
        help_text='Has this registration has been retracted?')
    pending_retraction = ser.BooleanField(source='is_pending_retraction', read_only=True,
        help_text='Is this registration pending retraction?')
    pending_approval = ser.BooleanField(source='sanction.pending_approval', read_only=True,
        help_text='Does this registration have a sanction pending approval?')
    date_registered = ser.DateTimeField(source='registered_date', read_only=True,
        help_text='Date time of registration.')
    pending_embargo = ser.BooleanField(read_only=True, source='is_pending_embargo',
        help_text='Is this registration pending embargo?')
    registered_meta = ser.DictField(read_only=True,
        help_text='Includes a dictionary with registration schema, embargo end date, and supplemental registration questions')

    registered_by = JSONAPIHyperlinkedIdentityField(
        view_name='users:user-detail',
        lookup_field='registered_user_id',
        link_type='related',
        lookup_url_kwarg='user_id'
    )

    registered_from = JSONAPIHyperlinkedIdentityField(
        view_name='nodes:node-detail',
        lookup_field='registered_from_id',
        link_type='related',
        lookup_url_kwarg='node_id'
    )

    # TODO: Finish me

    # TODO: Override create?

    links = LinksField({'self': 'get_registration_url', 'html': 'get_absolute_url'})

    def get_registration_url(self, obj):
        return absolute_reverse('registrations:registration-detail', kwargs={'registration_id': obj._id})

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def update(self, *args, **kwargs):
        raise exceptions.APIException('Registrations cannot be modified.')

    class Meta:
        type_ = 'registrations'


class RegistrationDetailSerializer(RegistrationSerializer):
    """
    Overrides NodeSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
