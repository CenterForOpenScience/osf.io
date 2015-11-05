from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeSerializer
from api.base.serializers import IDField, JSONAPIHyperlinkedIdentityField, LinksField, CheckRetraction, DevOnly


class RegistrationSerializer(NodeSerializer):

    filterable_fields = frozenset([
        'title',
        'description',
        'public',
        'registration',
        'tags',
        'category',
        'date_created',
        'date_modified',
        'retracted',
        'registered_by',
        'registered_from'
    ])
    retracted = ser.BooleanField(source='is_retracted', read_only=True,
        help_text='Whether this registration has been retracted.')
    date_registered = ser.DateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')
    justification = ser.CharField(source='retraction.justification', read_only=True)
    pending_retraction = CheckRetraction(ser.BooleanField(source='is_pending_retraction', read_only=True,
        help_text='Is this registration pending retraction?'))
    pending_registration_approval = CheckRetraction(ser.BooleanField(source='sanction.pending_approval', read_only=True,
        help_text='Does this registration have a sanction pending approval?'))
    pending_embargo = CheckRetraction(ser.BooleanField(read_only=True, source='is_pending_embargo',
        help_text='Is this registration pending embargo?'))
    registered_meta = CheckRetraction(ser.DictField(read_only=True,
        help_text='Includes a dictionary with registration schema, embargo end date, and supplemental registration questions'))
    registration_supplement = ser.SerializerMethodField()

    registered_by = CheckRetraction(JSONAPIHyperlinkedIdentityField(
        view_name='users:user-detail',
        lookup_field='registered_user_id',
        link_type='related',
        lookup_url_kwarg='user_id'
    ))

    registered_from = CheckRetraction(JSONAPIHyperlinkedIdentityField(
        view_name='nodes:node-detail',
        lookup_field='registered_from_id',
        link_type='related',
        lookup_url_kwarg='node_id'
    ))

    children = CheckRetraction(JSONAPIHyperlinkedIdentityField(view_name='registrations:registration-children', lookup_field='pk', link_type='related',
                                                lookup_url_kwarg='node_id', meta={'count': 'get_node_count'}))

    contributors = JSONAPIHyperlinkedIdentityField(view_name='registrations:registration-contributors', lookup_field='pk', link_type='related',
                                                    lookup_url_kwarg='node_id', meta={'count': 'get_contrib_count'})

    files = CheckRetraction(JSONAPIHyperlinkedIdentityField(view_name='registrations:registration-providers', lookup_field='pk', lookup_url_kwarg='node_id',
                                             link_type='related'))

    comments = CheckRetraction(JSONAPIHyperlinkedIdentityField(view_name='registrations:registration-comments', lookup_field='pk', lookup_url_kwarg='node_id',
                                               link_type='related', meta={'unread': 'get_unread_comments_count'}))

    node_links = CheckRetraction(DevOnly(JSONAPIHyperlinkedIdentityField(view_name='registrations:registration-pointers', lookup_field='pk', link_type='related',
                                                  lookup_url_kwarg='node_id', meta={'count': 'get_pointers_count'})))

    parent = CheckRetraction(JSONAPIHyperlinkedIdentityField(view_name='registrations:registration-detail', lookup_field='parent_id', link_type='related',
                                              lookup_url_kwarg='node_id'))

    registrations = CheckRetraction(DevOnly(JSONAPIHyperlinkedIdentityField(view_name='registrations:registration-registrations', lookup_field='pk', link_type='related',
                                                     lookup_url_kwarg='node_id', meta={'count': 'get_registration_count'})))

    forked_from = CheckRetraction(JSONAPIHyperlinkedIdentityField(
        view_name='nodes:node-detail',
        lookup_field='forked_from_id',
        link_type='related',
        lookup_url_kwarg='node_id'
    ))

    # TODO: Finish me

    # TODO: Override create?

    links = LinksField({'self': 'get_registration_url', 'html': 'get_absolute_url'})

    def get_registration_url(self, obj):
        return absolute_reverse('registrations:registration-detail', kwargs={'registration_id': obj._id})

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def get_registration_supplement(self, obj):
        if obj.registered_meta:
            return obj.registered_meta.keys()[0]
        return None

    def update(self, *args, **kwargs):
        raise exceptions.APIException('Registrations cannot be modified.')

    class Meta:
        type_ = 'registrations'


class RegistrationDetailSerializer(RegistrationSerializer):
    """
    Overrides NodeSerializer to make id required.
    """
    id = IDField(source='_id', required=True)
