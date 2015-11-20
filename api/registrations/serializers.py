from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeSerializer
from api.base.serializers import IDField, RelationshipField, LinksField


class RegistrationSerializer(NodeSerializer):

    retracted = ser.BooleanField(source='is_retracted', read_only=True,
        help_text='Whether this registration has been retracted.')
    date_registered = ser.DateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')

    registered_by = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<registered_user_id>'}
    )

    registered_from = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<registered_from_id>'}
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
