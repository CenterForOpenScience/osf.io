from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.serializers import JSONAPISerializer
from api.base.serializers import IDField, JSONAPIHyperlinkedRelatedField, LinksField


class RegistrationSerializer(JSONAPISerializer):

    id = IDField(source='_id', read_only=True)
    registration = ser.BooleanField(read_only=True, source='is_registration')
    retracted = ser.BooleanField(source='is_retracted', read_only=True,
        help_text='Whether this registration has been retracted.')
    registered_date = ser.DateTimeField(read_only=True)
    registered_meta = ser.CharField(read_only=True)
    embargo_end_date = ser.CharField(read_only=True, source='embargo.end_date')
    registered_schema = ser.CharField(read_only=True)

    branched_from = JSONAPIHyperlinkedRelatedField(view_name='nodes:node-detail', lookup_field='pk', link_type='related',
                                              lookup_url_kwarg='node_id', read_only=True, source='registered_from')
    initiator = JSONAPIHyperlinkedRelatedField(view_name='users:user-detail', lookup_field='pk', link_type='related',
                                              lookup_url_kwarg='user_id', read_only=True, source='registered_user')

    links = LinksField({'html': 'get_absolute_url'})

    class Meta:
        type_ = 'registrations'

    # TODO: Finish me

    # TODO: Override create?

    def update(self, *args, **kwargs):
        raise exceptions.ValidationError('Registrations cannot be modified.')


    def get_absolute_url(self, obj):
        return obj.absolute_url


class RegistrationDetailSerializer(RegistrationSerializer):
    """
    Overrides NodeSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
