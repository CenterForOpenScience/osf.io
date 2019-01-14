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
from api.nodes.serializers import NodeSerializer, NodeStorageProviderSerializer
from api.nodes.serializers import NodeLinksSerializer, NodeLicenseSerializer
from api.nodes.serializers import NodeContributorsSerializer, RegistrationProviderRelationshipField
from api.base.serializers import (
    IDField, RelationshipField, LinksField, HideIfWithdrawal,
    FileCommentRelationshipField, NodeFileHyperLinkField, HideIfRegistration,
    ShowIfVersion, VersionedDateTimeField, ValuesListField,
)
from framework.auth.core import Auth
from osf.exceptions import ValidationValueError
from osf.models import Node
from osf.utils import permissions

from framework.sentry import log_exception

class RegistrationSerializer(NodeSerializer):

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
    public = HideIfWithdrawal(ser.BooleanField(
        source='is_public', required=False,
               help_text='Nodes that are made public will give read-only access '
        'to everyone. Private nodes require explicit read '
        'permission. Write and admin access are the same for '
        'public and private nodes. Administrators on a parent '
        'node have implicit read permissions for all child nodes',
    ))
    current_user_permissions = HideIfWithdrawal(ser.SerializerMethodField(
        help_text='List of strings representing the permissions '
        'for the current user on this node.',
    ))

    pending_embargo_approval = HideIfWithdrawal(ser.BooleanField(
        read_only=True, source='is_pending_embargo',
        help_text='The associated Embargo is awaiting approval by project admins.',
    ))
    pending_embargo_termination_approval = HideIfWithdrawal(ser.BooleanField(
        read_only=True, source='is_pending_embargo_termination',
        help_text='The associated Embargo early termination is awaiting approval by project admins',
    ))
    embargoed = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_embargoed'))
    pending_registration_approval = HideIfWithdrawal(ser.BooleanField(
        source='is_pending_registration', read_only=True,
        help_text='The associated RegistrationApproval is awaiting approval by project admins.',
    ))
    archiving = HideIfWithdrawal(ser.BooleanField(read_only=True))
    pending_withdrawal = HideIfWithdrawal(ser.BooleanField(
        source='is_pending_retraction', read_only=True,
        help_text='The registration is awaiting withdrawal approval by project admins.',
    ))
    withdrawn = ser.BooleanField(
        source='is_retracted', read_only=True,
        help_text='The registration has been withdrawn.',
    )

    date_registered = VersionedDateTimeField(source='registered_date', read_only=True, help_text='Date time of registration.')
    date_withdrawn = VersionedDateTimeField(source='retraction.date_retracted', read_only=True, help_text='Date time of when this registration was retracted.')
    embargo_end_date = HideIfWithdrawal(ser.SerializerMethodField(help_text='When the embargo on this registration will be lifted.'))
    custom_citation = HideIfWithdrawal(ser.CharField(allow_blank=True, required=False))

    withdrawal_justification = ser.CharField(source='retraction.justification', read_only=True)
    template_from = HideIfWithdrawal(ser.CharField(
        read_only=True, allow_blank=False, allow_null=False,
        help_text='Specify a node id for a node you would like to use as a template for the '
        'new node. Templating is like forking, except that you do not copy the '
        'files, only the project structure. Some information is changed on the top '
        'level project by submitting the appropriate fields in the request body, '
        'and some information will not change. By default, the description will '
        'be cleared and the project will be made private.',
    ))
    registration_supplement = ser.SerializerMethodField()
    registered_meta = HideIfWithdrawal(ser.SerializerMethodField(
        help_text='A dictionary with supplemental registration questions and responses.',
    ))

    registered_by = HideIfWithdrawal(RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<registered_user._id>'},
    ))

    registered_from = HideIfWithdrawal(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<registered_from._id>'},
    ))

    children = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-children',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_count'},
    ))

    comments = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-comments',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={
            'unread': 'get_unread_comments_count',
            'total': 'get_total_comments_count',  # total count of top_level, undeleted comments on the registration (node)
        },
        filter={'target': '<_id>'},
    ))

    contributors = RelationshipField(
        related_view='registrations:registration-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_contrib_count'},
    )

    implicit_contributors = RelationshipField(
        related_view='registrations:registration-implicit-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        help_text='This feature is experimental and being tested. It may be deprecated.',
    )

    files = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-storage-providers',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    wikis = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-wikis',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_wiki_page_count'},
    ))

    forked_from = HideIfWithdrawal(RelationshipField(
        related_view=lambda n: 'registrations:registration-detail' if getattr(n, 'is_registration', False) else 'nodes:node-detail',
        related_view_kwargs={'node_id': '<forked_from_id>'},
    ))

    template_node = HideIfWithdrawal(RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<template_node._id>'},
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
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_forks_count'},
    ))

    node_links = ShowIfVersion(
        HideIfWithdrawal(RelationshipField(
            related_view='registrations:registration-pointers',
            related_view_kwargs={'node_id': '<_id>'},
            related_meta={'count': 'get_pointers_count'},
            help_text='This feature is deprecated as of version 2.1. Use linked_nodes instead.',
        )), min_version='2.0', max_version='2.0',
    )

    linked_by_nodes = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-linked-by-nodes',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_linked_by_nodes_count'},
    ))

    linked_by_registrations = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-linked-by-registrations',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_linked_by_registrations_count'},
    ))

    parent = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node',
    ))

    root = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<root._id>'},
    ))

    region = HideIfWithdrawal(RelationshipField(
        related_view='regions:region-detail',
        related_view_kwargs={'region_id': '<osfstorage_region._id>'},
        read_only=True,
    ))

    affiliated_institutions = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-institutions',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    registration_schema = RelationshipField(
        related_view='schemas:registration-schema-detail',
        related_view_kwargs={'schema_id': '<registered_schema_id>'},
    )

    settings = HideIfRegistration(RelationshipField(
        related_view='nodes:node-settings',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-registrations',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    draft_registrations = HideIfRegistration(RelationshipField(
        related_view='nodes:node-draft-registrations',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    preprints = HideIfWithdrawal(HideIfRegistration(RelationshipField(
        related_view='nodes:node-preprints',
        related_view_kwargs={'node_id': '<_id>'},
    )))

    identifiers = HideIfWithdrawal(RelationshipField(
        related_view='registrations:identifier-list',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    linked_nodes = HideIfWithdrawal(RelationshipField(
        related_view='registrations:linked-nodes',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_node_links_count'},
        self_view='registrations:node-pointer-relationship',
        self_view_kwargs={'node_id': '<_id>'},
    ))

    linked_registrations = HideIfWithdrawal(RelationshipField(
        related_view='registrations:linked-registrations',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_registration_links_count'},
        self_view='registrations:node-registration-pointer-relationship',
        self_view_kwargs={'node_id': '<_id>'},
    ))

    view_only_links = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-view-only-links',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_view_only_links_count'},
    ))

    citation = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-citation',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    provider = RegistrationProviderRelationshipField(
        related_view='providers:registration-providers:registration-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=True,
    )

    links = LinksField({'self': 'get_registration_url', 'html': 'get_absolute_html_url'})

    def get_registration_url(self, obj):
        return absolute_reverse(
            'registrations:registration-detail', kwargs={
                'node_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

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
            schema = obj.registered_schema.first()
            if schema is None:
                return None
            return schema.name
        return None

    def get_current_user_permissions(self, obj):
        return NodeSerializer.get_current_user_permissions(self, obj)

    def get_view_only_links_count(self, obj):
        return obj.private_links.filter(is_deleted=False).count()

    def get_total_comments_count(self, obj):
        return {
            'node': obj.comment_set.filter(page='node', target___id=obj._id, is_deleted=False).count(),
        }

    def update(self, registration, validated_data):
        # TODO - when withdrawal is added, make sure to restrict to admin only here
        user = self.context['request'].user
        auth = Auth(user)
        user_is_admin = registration.has_permission(user, permissions.ADMIN)
        # Update tags
        if 'tags' in validated_data:
            new_tags = validated_data.pop('tags', [])
            try:
                registration.update_tags(new_tags, auth=auth)
            except NodeStateError as err:
                raise Conflict(str(err))
        if 'custom_citation' in validated_data:
            if user_is_admin:
                registration.update_custom_citation(validated_data.pop('custom_citation'), auth)
            else:
                raise exceptions.PermissionDenied()
        is_public = validated_data.get('is_public', None)
        if is_public is not None:
            if is_public:
                if user_is_admin:
                    try:
                        registration.update(validated_data, auth=auth)
                    except NodeUpdateError as err:
                        raise exceptions.ValidationError(err.reason)
                    except NodeStateError as err:
                        raise exceptions.ValidationError(str(err))
                else:
                    raise exceptions.PermissionDenied()
            else:
                raise exceptions.ValidationError('Registrations can only be turned from private to public.')
        return registration

    class Meta:
        type_ = 'registrations'


class RegistrationCreateSerializer(RegistrationSerializer):
    """
    Overrides RegistrationSerializer to add draft_registration, registration_choice, and lift_embargo fields
    """
    draft_registration = ser.CharField(write_only=True)
    registration_choice = ser.ChoiceField(write_only=True, choices=['immediate', 'embargo'])
    lift_embargo = VersionedDateTimeField(write_only=True, default=None, input_formats=['%Y-%m-%dT%H:%M:%S'])
    children = ser.ListField(write_only=True, required=False)

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        draft = validated_data.pop('draft')
        registration_choice = validated_data.pop('registration_choice', 'immediate')
        embargo_lifted = validated_data.pop('lift_embargo', None)
        reviewer = is_prereg_admin_not_project_admin(self.context['request'], draft)
        children = validated_data.pop('children', [])
        if children:
            # First check that all children are valid
            child_nodes = Node.objects.filter(guids___id__in=children)
            if child_nodes.count() != len(children):
                raise exceptions.ValidationError('Some child nodes could not be found.')

        # Second check that metadata doesn't have files that are not in the child nodes being registered.
        registering = children + [draft.branched_from._id]
        orphan_files = self._find_orphan_files(registering, draft)
        if orphan_files:
            orphan_files_names = [file_data['selectedFileName'] for file_data in orphan_files]
            raise exceptions.ValidationError('All files attached to this form must be registered to complete the process. '
                                             'The following file(s) are attached, but are not part of a component being'
                                             ' registered: {}'.format(','.join(orphan_files_names)))

        try:
            draft.validate_metadata(metadata=draft.registration_metadata, reviewer=reviewer, required_fields=True)
        except ValidationValueError:
            log_exception()  # Probably indicates a bug on our end, so log to sentry
            # TODO: Raise an error once our JSON schemas are updated

        try:
            registration = draft.register(auth, save=True, child_ids=children)
        except NodeStateError as err:
            raise exceptions.ValidationError(err)

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

    def _find_orphan_files(self, registering, draft):
        from website.archiver.utils import find_selected_files
        files = find_selected_files(draft.registration_schema, draft.registration_metadata)
        orphan_files = []
        for _, value in files.items():
            if 'extra' in value:
                for file_metadata in value['extra']:
                    if file_metadata['nodeId'] not in registering:
                        orphan_files.append(file_metadata)
        return orphan_files


class RegistrationDetailSerializer(RegistrationSerializer):
    """
    Overrides RegistrationSerializer to make id required.
    """

    id = IDField(source='_id', required=True)


class RegistrationNodeLinksSerializer(NodeLinksSerializer):
    def get_absolute_url(self, obj):
        return absolute_reverse(
            'registrations:registration-pointer-detail',
            kwargs={
                'node_link_id': obj._id,
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class RegistrationContributorsSerializer(NodeContributorsSerializer):
    def get_absolute_url(self, obj):
        return absolute_reverse(
            'registrations:registration-contributor-detail',
            kwargs={
                'user_id': obj.user._id,
                'node_id': self.context['request'].parser_context['kwargs']['node_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class RegistrationFileSerializer(OsfStorageFileSerializer):

    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<target._id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
    )

    comments = FileCommentRelationshipField(
        related_view='registrations:registration-comments',
        related_view_kwargs={'node_id': '<target._id>'},
        related_meta={'unread': 'get_unread_comments_count'},
        filter={'target': 'get_file_guid'},
    )

    node = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<target._id>'},
        help_text='The registration that this file belongs to',
    )

class RegistrationStorageProviderSerializer(NodeStorageProviderSerializer):
    """
    Overrides NodeStorageProviderSerializer to lead to correct registration file links
    """
    files = NodeFileHyperLinkField(
        related_view='registrations:registration-files',
        related_view_kwargs={'node_id': '<target._id>', 'path': '<path>', 'provider': '<provider>'},
        kind='folder',
        never_embed=True,
    )
