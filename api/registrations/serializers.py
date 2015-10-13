from rest_framework import serializers as ser
from rest_framework import exceptions

from api.nodes.serializers import NodeSerializer
from api.base.serializers import IDField, JSONAPIHyperlinkedIdentityField, LinksField


class RegistrationSerializer(NodeSerializer):

    retracted = ser.BooleanField(source='is_retracted', read_only=True,
        help_text='Whether this registration has been retracted.')
    date_registered = ser.DateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')

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

    links = LinksField({'html': 'get_absolute_url'})

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def update(self, *args, **kwargs):
        raise exceptions.ValidationError('Registrations cannot be modified.')

    class Meta:
        type_ = 'registrations'


class RegistrationDetailSerializer(RegistrationSerializer):
    """
    Overrides NodeSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
