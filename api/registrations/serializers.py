import json
from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse
from api.nodes.serializers import NodeSerializer
from api.base.serializers import IDField, RelationshipField, LinksField, HideIfRetraction, DevOnly


class RegistrationSerializer(NodeSerializer):

    retracted = ser.BooleanField(source='is_retracted', read_only=True,
                                 help_text='Whether this registration has been retracted.')
    date_registered = ser.DateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')
    retraction_justification = ser.CharField(source='retraction.justification', read_only=True)
    pending_retraction = HideIfRetraction(ser.BooleanField(source='is_pending_retraction', read_only=True,
        help_text='Is this registration pending retraction?'))
    pending_registration_approval = HideIfRetraction(ser.BooleanField(source='sanction.pending_approval', read_only=True,
        help_text='Does this registration have a sanction pending approval?'))
    pending_embargo = HideIfRetraction(ser.BooleanField(read_only=True, source='is_pending_embargo',
        help_text='Is this registration pending embargo?'))
    registered_meta = HideIfRetraction(ser.SerializerMethodField(
        help_text='A dictionary with embargo end date, whether registration choice was immediate or embargoed,'
                  ' and answers to supplemental registration questions'))
    registration_supplement = ser.SerializerMethodField()

    registered_by = HideIfRetraction(RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<registered_user_id>'}
    ))

    registered_from = HideIfRetraction(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<registered_from_id>'}
    ))

    children = HideIfRetraction(RelationshipField(
        related_view='registrations:registration-children',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_node_count'},
    ))

    comments = HideIfRetraction(RelationshipField(
        related_view='registrations:registration-comments',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'unread': 'get_unread_comments_count'}))

    contributors = RelationshipField(
        related_view='registrations:registration-contributors',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_contrib_count'}
    )

    files = HideIfRetraction(RelationshipField(
        related_view='registrations:registration-providers',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    forked_from = HideIfRetraction(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<forked_from_id>'}
    ))

    node_links = DevOnly(HideIfRetraction(RelationshipField(
        related_view='registrations:registration-pointers',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_pointers_count'}
    )))

    parent = HideIfRetraction(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<parent_id>'}
    ))

    # TODO: Finish me

    # TODO: Override create?

    links = LinksField({'self': 'get_registration_url', 'html': 'get_absolute_url'})

    def get_registration_url(self, obj):
        return absolute_reverse('registrations:registration-detail', kwargs={'registration_id': obj._id})

    def get_absolute_url(self, obj):
        return obj.absolute_url

    def get_registered_meta(self, obj):
        if obj.registered_meta:
            meta_values = obj.registered_meta.values()[0]
            try:
                return json.loads(meta_values)
            except TypeError:
                return meta_values
            except ValueError:
                return meta_values
        return None

    def get_registration_supplement(self, obj):
        if obj.registered_schema:
            schema = obj.registered_schema[0]
            if schema is None:
                return None
            return schema.name
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
