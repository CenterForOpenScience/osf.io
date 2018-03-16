import pytz
import json

from django.core.exceptions import ValidationError
from rest_framework import serializers as ser
from rest_framework import exceptions
from api.base.exceptions import Conflict

from api.base.utils import absolute_reverse, get_user_auth
from website.project.metadata.utils import is_prereg_admin_not_project_admin
from website.exceptions import NodeStateError
from website.project.model import NodeUpdateError

from api.files.serializers import OsfStorageFileSerializer
from api.nodes.serializers import NodeSerializer, NodeProviderSerializer
from api.nodes.serializers import NodeLinksSerializer, NodeLicenseSerializer
from api.nodes.serializers import NodeContributorsSerializer
from api.base.serializers import (IDField, RelationshipField, LinksField, HideIfWithdrawal,
                                  FileCommentRelationshipField, NodeFileHyperLinkField, HideIfRegistration,
                                  ShowIfVersion, VersionedDateTimeField, ValuesListField)
from framework.auth.core import Auth
from osf.exceptions import ValidationValueError


class BaseRegistrationSerializer(NodeSerializer):

    title = ser.CharField(read_only=True)
    description = ser.CharField(read_only=True)
    category_choices = NodeSerializer.category_choices
    category_choices_string = NodeSerializer.category_choices_string
    category = HideIfWithdrawal(ser.ChoiceField(read_only=True, choices=category_choices, help_text='Choices: ' + category_choices_string))
    date_modified = VersionedDateTimeField(source='last_logged', read_only=True)
    fork = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_fork'))
    collection = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_collection'))
    access_requests_enabled = HideIfWithdrawal(ser.BooleanField(read_only=True))
    node_license = HideIfWithdrawal(NodeLicenseSerializer(read_only=True))
    tags = HideIfWithdrawal(ValuesListField(attr_name='name', child=ser.CharField(), required=False))
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

    date_registered = VersionedDateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')
    date_withdrawn = VersionedDateTimeField(source='retraction.date_retracted', read_only=True, help_text='Date time of when this registration was retracted.')
    embargo_end_date = HideIfWithdrawal(ser.SerializerMethodField(help_text='When the embargo on this registration will be lifted.'))

    withdrawal_justification = ser.CharField(source='retraction.justification', read_only=True)
    template_from = HideIfWithdrawal(ser.CharField(read_only=True, allow_blank=False, allow_null=False,
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
        related_view_kwargs={'user_id': '<registered_user._id>'}
    ))

    registered_from = HideIfWithdrawal(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<registered_from._id>'}
    ))

    children = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-children',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_count'},
    ))

    comments = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-comments',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': '<_id>'}
    ))

    contributors = RelationshipField(
        related_view='registrations:registration-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_contrib_count'}
    )

    implicit_contributors = RelationshipField(
        related_view='registrations:registration-implicit-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        help_text='This feature is experimental and being tested. It may be deprecated.'
    )

    files = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-providers',
        related_view_kwargs={'node_id': '<_id>'}
    ))

    wikis = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-wikis',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    forked_from = HideIfWithdrawal(RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<forked_from_id>'}
    ))

    template_node = HideIfWithdrawal(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<template_node._id>'}
    ))

    license = HideIfWithdrawal(RelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<node_license.node_license._id>'},
    ))

    logs = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-logs',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    forks = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-forks',
        related_view_kwargs={'node_id': '<_id>'}
    ))

    node_links = ShowIfVersion(HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-pointers',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_pointers_count'},
        help_text='This feature is deprecated as of version 2.1. Use linked_nodes instead.'
    )), min_version='2.0', max_version='2.0')

    parent = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node'
    ))

    root = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<root._id>'}
    ))

    affiliated_institutions = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-institutions',
        related_view_kwargs={'node_id': '<_id>'}
    ))

    registration_schema = RelationshipField(
        related_view='metaschemas:metaschema-detail',
        related_view_kwargs={'metaschema_id': '<registered_schema_id>'}
    )

    registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-registrations',
        related_view_kwargs={'node_id': '<_id>'}
    ))

    draft_registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-draft-registrations',
        related_view_kwargs={'node_id': '<_id>'}
    ))

    preprints = HideIfWithdrawal(HideIfRegistration(RelationshipField(
        related_view='nodes:node-preprints',
        related_view_kwargs={'node_id': '<_id>'}
    )))

    identifiers = HideIfWithdrawal(RelationshipField(
        related_view='registrations:identifier-list',
        related_view_kwargs={'node_id': '<_id>'}
    ))

    linked_nodes = HideIfWithdrawal(RelationshipField(
        related_view='registrations:linked-nodes',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_links_count'},
        self_view='registrations:node-pointer-relationship',
        self_view_kwargs={'node_id': '<_id>'}
    ))

    linked_registrations = HideIfWithdrawal(RelationshipField(
        related_view='registrations:linked-registrations',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_registration_links_count'},
        self_view='registrations:node-registration-pointer-relationship',
        self_view_kwargs={'node_id': '<_id>'}
    ))

    view_only_links = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-view-only-links',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_view_only_links_count'},
    ))

    citation = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-citation',
        related_view_kwargs={'node_id': '<_id>'}
    ))

    links = LinksField({'self': 'get_registration_url', 'html': 'get_absolute_html_url'})

    def get_registration_url(self, obj):
        return absolute_reverse('registrations:registration-detail', kwargs={
            'node_id': obj._id,
            'version': self.context['request'].parser_context['kwargs']['version']
        })

    def get_absolute_url(self, obj):
        return self.get_registration_url(obj)

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        draft = validated_data.pop('draft')
        registration_choice = validated_data.pop('registration_choice', 'immediate')
        embargo_lifted = validated_data.pop('lift_embargo', None)
        reviewer = is_prereg_admin_not_project_admin(self.context['request'], draft)

        try:
            draft.validate_metadata(metadata=draft.registration_metadata, reviewer=reviewer, required_fields=True)
        except ValidationValueError as e:
            raise exceptions.ValidationError(e.message)

        registration = draft.register(auth, save=True)

        if registration_choice == 'embargo':
            if not embargo_lifted:
                raise exceptions.ValidationError('lift_embargo must be specified.')
            embargo_end_date = embargo_lifted.replace(tzinfo=pytz.utc)
            try:
                registration.embargo_registration(auth.user, embargo_end_date)
            except ValidationError as err:
                raise exceptions.ValidationError(err.message)
        else:
            try:
                registration.require_approval(auth.user)
            except NodeStateError as err:
                raise exceptions.ValidationError(err)

        registration.save()
        return registration

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
            schema = obj.registered_schema.first()
            if schema is None:
                return None
            return schema.name
        return None

    def get_current_user_permissions(self, obj):
        return NodeSerializer.get_current_user_permissions(self, obj)

    def update(self, registration, validated_data):
        auth = Auth(self.context['request'].user)
        # Update tags
        if 'tags' in validated_data:
            new_tags = validated_data.pop('tags', [])
            try:
                registration.update_tags(new_tags, auth=auth)
            except NodeStateError as err:
                raise Conflict(err.message)

        is_public = validated_data.get('is_public', None)
        if is_public is not None:
            if is_public:
                try:
                    registration.update(validated_data, auth=auth)
                except NodeUpdateError as err:
                    raise exceptions.ValidationError(err.reason)
                except NodeStateError as err:
                    raise exceptions.ValidationError(err.message)
            else:
                raise exceptions.ValidationError('Registrations can only be turned from private to public.')
        return registration

    class Meta:
        type_ = 'registrations'


class RegistrationSerializer(BaseRegistrationSerializer):
    """
    Overrides BaseRegistrationSerializer to add draft_registration, registration_choice, and lift_embargo fields
    """
    draft_registration = ser.CharField(write_only=True)
    registration_choice = ser.ChoiceField(write_only=True, choices=['immediate', 'embargo'])
    lift_embargo = VersionedDateTimeField(write_only=True, default=None, input_formats=['%Y-%m-%dT%H:%M:%S'])


class RegistrationDetailSerializer(BaseRegistrationSerializer):
    """
    Overrides BaseRegistrationSerializer to make id required.
    """

    id = IDField(source='_id', required=True)


class RegistrationNodeLinksSerializer(NodeLinksSerializer):
    def get_absolute_url(self, obj):
        return absolute_reverse(
            'registrations:registration-pointer-detail',
            kwargs={
                'node_link_id': obj._id,
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )


class RegistrationContributorsSerializer(NodeContributorsSerializer):
    def get_absolute_url(self, obj):
        return absolute_reverse(
            'registrations:registration-contributor-detail',
            kwargs={
                'user_id': obj.user._id,
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version']
            }
        )


class RegistrationFileSerializer(OsfStorageFileSerializer):

    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<node._id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder'
    )

    comments = FileCommentRelationshipField(related_view='registrations:registration-comments',
                                            related_view_kwargs={'node_id': '<node._id>'},
                                            related_meta={'unread': 'get_unread_comments_count'},
                                            filter={'target': 'get_file_guid'}
                                            )

    node = RelationshipField(related_view='registrations:registration-detail',
                                     related_view_kwargs={'node_id': '<node._id>'},
                                     help_text='The registration that this file belongs to'
                             )

class RegistrationProviderSerializer(NodeProviderSerializer):
    """
    Overrides NodeProviderSerializer to lead to correct registration file links
    """
    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<node._id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
        never_embed=True
    )
