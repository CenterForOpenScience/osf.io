import json
from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse
from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer
from api.nodes.serializers import NodeLinksSerializer
from api.nodes.serializers import NodeContributorsSerializer
from api.base.serializers import (IDField, RelationshipField, LinksField, HideIfRetraction, DevOnly,
                                  FileCommentRelationshipField, NodeFileHyperLinkField)


class RegistrationSerializer(NodeSerializer):

    pending_embargo_approval = HideIfRetraction(ser.BooleanField(read_only=True, source='is_pending_embargo',
        help_text='The associated Embargo is awaiting approval by project admins.'))
    pending_registration_approval = HideIfRetraction(ser.BooleanField(source='is_pending_registration', read_only=True,
        help_text='The associated RegistrationApproval is awaiting approval by project admins.'))
    pending_withdrawal = HideIfRetraction(ser.BooleanField(source='is_pending_retraction', read_only=True,
        help_text='The registration is awaiting withdrawal approval by project admins.'))
    withdrawn = ser.BooleanField(source='is_retracted', read_only=True,
                                 help_text='The registration has been withdrawn.')

    date_registered = ser.DateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')
    embargo_end_date = HideIfRetraction(ser.SerializerMethodField(help_text='When the embargo on this registration will be lifted.'))

    withdrawal_justification = ser.CharField(source='retraction.justification', read_only=True)
    registration_supplement = ser.SerializerMethodField()
    registered_meta = HideIfRetraction(ser.SerializerMethodField(
        help_text='A dictionary with supplemental registration questions and responses.'))

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
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node'
    ))

    logs = HideIfRetraction(RelationshipField(
        related_view='registrations:registration-logs',
        related_view_kwargs={'node_id': '<pk>'},
    ))

    root = HideIfRetraction(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<root._id>'}
    ))

    primary_institution = RelationshipField(
        related_view='registrations:registration-institution-detail',
        related_view_kwargs={'node_id': '<pk>'}
    )
    registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-registrations',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    # TODO: Finish me

    # TODO: Override create?

    links = LinksField({'self': 'get_registration_url', 'html': 'get_absolute_html_url'})

    def get_registration_url(self, obj):
        return absolute_reverse('registrations:registration-detail', kwargs={'node_id': obj._id})

    def get_absolute_url(self, obj):
        return self.get_registration_url(obj)

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

    def get_embargo_end_date(self, obj):
        if obj.embargo_end_date:
            return obj.embargo_end_date
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


class RegistrationNodeLinksSerializer(NodeLinksSerializer):
    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'registrations:registration-pointer-detail',
            kwargs={
                'node_id': node_id,
                'node_link_id': obj._id
            }
        )


class RegistrationContributorsSerializer(NodeContributorsSerializer):
    def get_absolute_url(self, obj):
        node_id = self.context['request'].parser_context['kwargs']['node_id']
        return absolute_reverse(
            'registrations:registration-contributor-detail',
            kwargs={
                'node_id': node_id,
                'user_id': obj._id
            }
        )


class RegistrationFileSerializer(FileSerializer):

    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<node_id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder'
    )

    comments = FileCommentRelationshipField(related_view='registrations:registration-comments',
                                            related_view_kwargs={'node_id': '<node._id>'},
                                            related_meta={'unread': 'get_unread_comments_count'},
                                            filter={'target': 'get_file_guid'})
