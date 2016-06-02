import json
from rest_framework import serializers as ser
from rest_framework import exceptions

from api.base.utils import absolute_reverse
from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer, NodeProviderSerializer
from api.nodes.serializers import NodeLinksSerializer
from api.nodes.serializers import NodeContributorsSerializer, NodeTagField
from api.base.serializers import (IDField, RelationshipField, LinksField, HideIfWithdrawal,
                                  FileCommentRelationshipField, NodeFileHyperLinkField, HideIfRegistration, JSONAPIListField)


class RegistrationSerializer(NodeSerializer):

    category_choices = NodeSerializer.category_choices
    category_choices_string = NodeSerializer.category_choices_string
    category = HideIfWithdrawal(ser.ChoiceField(choices=category_choices, help_text="Choices: " + category_choices_string))

    date_modified = HideIfWithdrawal(ser.DateTimeField(read_only=True))
    fork = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_fork'))
    collection = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_collection'))
    tags = HideIfWithdrawal(JSONAPIListField(child=NodeTagField(), required=False))
    public = HideIfWithdrawal(ser.BooleanField(source='is_public', required=False,
                                               help_text='Nodes that are made public will give read-only access '
                                        'to everyone. Private nodes require explicit read '
                                        'permission. Write and admin access are the same for '
                                        'public and private nodes. Administrators on a parent '
                                        'node have implicit read permissions for all child nodes'))
    current_user_permissions = HideIfWithdrawal(ser.SerializerMethodField(help_text='List of strings representing the permissions '
                                                                   'for the current user on this node.'))

    pending_embargo_approval = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_pending_embargo',
                                                                 help_text='The associated Embargo is awaiting approval by project admins.'))
    pending_registration_approval = HideIfWithdrawal(ser.BooleanField(source='is_pending_registration', read_only=True,
                                                                      help_text='The associated RegistrationApproval is awaiting approval by project admins.'))
    pending_withdrawal = HideIfWithdrawal(ser.BooleanField(source='is_pending_retraction', read_only=True,
                                                           help_text='The registration is awaiting withdrawal approval by project admins.'))
    withdrawn = ser.BooleanField(source='is_retracted', read_only=True,
                                 help_text='The registration has been withdrawn.')

    date_registered = ser.DateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')
    embargo_end_date = HideIfWithdrawal(ser.SerializerMethodField(help_text='When the embargo on this registration will be lifted.'))

    withdrawal_justification = ser.CharField(source='retraction.justification', read_only=True)
    template_from = HideIfWithdrawal(ser.CharField(required=False, allow_blank=False, allow_null=False,
                help_text='Specify a node id for a node you would like to use as a template for the '
                'new node. Templating is like forking, except that you do not copy the '
                'files, only the project structure. Some information is changed on the top '
                'level project by submitting the appropriate fields in the request body, '
                'and some information will not change. By default, the description will '
                'be cleared and the project will be made private.'))
    registration_supplement = ser.SerializerMethodField()
    registered_meta = HideIfWithdrawal(ser.SerializerMethodField(
        help_text='A dictionary with supplemental registration questions and responses.'))

    registered_by = HideIfWithdrawal(RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<registered_user_id>'}
    ))

    registered_from = HideIfWithdrawal(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<registered_from_id>'}
    ))

    children = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-children',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_node_count'},
    ))

    comments = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-comments',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'unread': 'get_unread_comments_count'}))

    contributors = RelationshipField(
        related_view='registrations:registration-contributors',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_contrib_count'}
    )

    files = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-providers',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    forked_from = HideIfWithdrawal(RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<forked_from_id>'}
    ))

    forks = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-forks',
        related_view_kwargs={'node_id': '<pk>'}
    ))

    node_links = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-pointers',
        related_view_kwargs={'node_id': '<pk>'},
        related_meta={'count': 'get_pointers_count'}
    ))

    parent = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node'
    ))

    logs = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-logs',
        related_view_kwargs={'node_id': '<pk>'},
    ))

    root = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<root._id>'}
    ))

    affiliated_institutions = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-institutions',
        related_view_kwargs={'node_id': '<pk>'}
    ))
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

    def get_current_user_permissions(self, obj):
        return NodeSerializer.get_current_user_permissions(self, obj)

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


class RegistrationProviderSerializer(NodeProviderSerializer):
    """
    Overrides NodeProviderSerializer to lead to correct registration file links
    """
    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<node_id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
        never_embed=True
    )
