import pytz
import json
from unicodedata import normalize

from distutils.version import StrictVersion
from django.core.exceptions import ValidationError
from rest_framework import serializers as ser
from rest_framework import exceptions
from api.base.exceptions import Conflict, InvalidModelValueError, JSONAPIException
from api.base.serializers import is_anonymized
from api.base.utils import absolute_reverse, get_user_auth, is_truthy
from api.base.versioning import CREATE_REGISTRATION_FIELD_CHANGE_VERSION
from website.project.model import NodeUpdateError

from api.files.serializers import OsfStorageFileSerializer
from api.nodes.serializers import (
    NodeSerializer,
    NodeStorageProviderSerializer,
    NodeLicenseRelationshipField,
    NodeLinksSerializer,
    update_institutions,
    NodeLicenseSerializer,
    NodeContributorsSerializer,
    RegistrationProviderRelationshipField,
    get_license_details,
)
from api.base.serializers import (
    IDField, RelationshipField, LinksField, HideIfWithdrawal,
    FileRelationshipField, NodeFileHyperLinkField, HideIfRegistration,
    ShowIfVersion, VersionedDateTimeField, ValuesListField,
)
from framework.auth.core import Auth
from osf.exceptions import ValidationValueError, NodeStateError
from osf.models import Node, AbstractNode
from osf.utils.registrations import strip_registered_meta_comments
from framework.sentry import log_exception

class RegistrationSerializer(NodeSerializer):
    admin_only_editable_fields = [
        'custom_citation',
        'is_pending_retraction',
        'is_public',
        'license',
        'license_type',
        'withdrawal_justification',
    ]

    # Remember to add new RegistrationSerializer fields to this list
    # if you don't need them to be anonymized
    non_anonymized_fields = NodeSerializer.non_anonymized_fields + [
        'archiving',
        'article_doi',
        'date_registered',
        'date_withdrawn',
        'embargo_end_date',
        'embargoed',
        'pending_embargo_approval',
        'pending_embargo_termination_approval',
        'pending_registration_approval',
        'pending_withdrawal',
        'provider',
        'registered_by',
        'registered_from',
        'registered_meta',
        'registration_responses',
        'registration_schema',
        'registration_supplement',
        'withdrawal_justification',
        'withdrawn',
    ]

    reviews_state = ser.CharField(source='moderation_state', read_only=True)
    title = ser.CharField(read_only=True)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    category_choices = NodeSerializer.category_choices
    category_choices_string = NodeSerializer.category_choices_string
    category = ser.ChoiceField(required=False, choices=category_choices, help_text='Choices: ' + category_choices_string)
    date_modified = VersionedDateTimeField(source='last_logged', read_only=True)
    fork = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_fork'))
    collection = HideIfWithdrawal(ser.BooleanField(read_only=True, source='is_collection'))
    access_requests_enabled = HideIfWithdrawal(ser.BooleanField(read_only=True))
    node_license = HideIfWithdrawal(NodeLicenseSerializer(required=False, source='license'))
    tags = HideIfWithdrawal(ValuesListField(attr_name='name', child=ser.CharField(), required=False))
    article_doi = ser.CharField(required=False, allow_null=True)
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
    date_withdrawn = VersionedDateTimeField(read_only=True, help_text='Date time of when this registration was retracted.')
    embargo_end_date = HideIfWithdrawal(ser.SerializerMethodField(help_text='When the embargo on this registration will be lifted.'))
    custom_citation = HideIfWithdrawal(ser.CharField(allow_blank=True, required=False))

    withdrawal_justification = ser.CharField(read_only=True)
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
    # Will be deprecated in favor of registration_responses
    registered_meta = HideIfWithdrawal(ser.SerializerMethodField(
        help_text='A dictionary with supplemental registration questions and responses.',
    ))
    registration_responses = HideIfWithdrawal(ser.SerializerMethodField(
        help_text='A dictionary with supplemental registration questions and responses.',
    ))
    registered_by = HideIfWithdrawal(RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<registered_user._id>'},
    ))

    registered_from = RelationshipField(
        related_view='nodes:node-detail',
        related_view_kwargs={'node_id': '<registered_from._id>'},
    )

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
            'count': 'get_total_comments_count',
        },
        filter={'target': '<_id>'},
    ))

    contributors = RelationshipField(
        related_view='registrations:registration-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_contrib_count'},
    )

    bibliographic_contributors = RelationshipField(
        related_view='registrations:registration-bibliographic-contributors',
        related_view_kwargs={'node_id': '<_id>'},
    )

    implicit_contributors = RelationshipField(
        related_view='registrations:registration-implicit-contributors',
        related_view_kwargs={'node_id': '<_id>'},
        help_text='This feature is experimental and being tested. It may be deprecated.',
    )

    files = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-storage-providers',
        related_view_kwargs={'node_id': '<_id>'},
        related_meta={'count': 'get_files_count'},
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

    license = HideIfWithdrawal(NodeLicenseRelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<license.node_license._id>'},
        read_only=False,
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

    groups = HideIfRegistration(RelationshipField(
        related_view='nodes:node-groups',
        related_view_kwargs={'node_id': '<_id>'},
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

    parent = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<parent_node._id>'},
        filter_key='parent_node',
    )

    root = RelationshipField(
        related_view='registrations:registration-detail',
        related_view_kwargs={'node_id': '<root._id>'},
    )

    region = HideIfWithdrawal(RelationshipField(
        related_view='regions:region-detail',
        related_view_kwargs={'region_id': '<osfstorage_region._id>'},
        read_only=True,
    ))

    affiliated_institutions = RelationshipField(
        related_view='registrations:registration-institutions',
        related_view_kwargs={'node_id': '<_id>'},
        self_view='registrations:registration-relationships-institutions',
        self_view_kwargs={'node_id': '<_id>'},
        read_only=False,
        many=True,
        required=False,
    )

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

    identifiers = RelationshipField(
        related_view='registrations:identifier-list',
        related_view_kwargs={'node_id': '<_id>'},
    )

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

    review_actions = RelationshipField(
        related_view='registrations:registration-actions-list',
        related_view_kwargs={'node_id': '<_id>'},
    )

    requests = HideIfWithdrawal(RelationshipField(
        related_view='registrations:registration-requests-list',
        related_view_kwargs={'node_id': '<_id>'},
    ))

    @property
    def subjects_related_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'registrations:registration-subjects'

    @property
    def subjects_self_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'registrations:registration-relationships-subjects'

    links = LinksField({'html': 'get_absolute_html_url'})

    def get_absolute_url(self, obj):
        return obj.get_absolute_url()

    def get_registered_meta(self, obj):
        if obj.registered_meta:
            meta_values = self.anonymize_registered_meta(obj)
            try:
                return json.loads(meta_values)
            except TypeError:
                return meta_values
            except ValueError:
                return meta_values
        return None

    def get_registration_responses(self, obj):
        if obj.registration_responses:
            return self.anonymize_registration_responses(obj)
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
        return obj.comment_set.filter(page='node', is_deleted=False).count()

    def get_files_count(self, obj):
        return obj.files_count or 0

    def anonymize_registered_meta(self, obj):
        """
        Looks at every question on every page of the schema, for any titles
        that have a contributor-input block type.  If present, deletes that question's response
        from meta_values.
        """
        cleaned_registered_meta = strip_registered_meta_comments(list(obj.registered_meta.values())[0])
        return self.anonymize_fields(obj, cleaned_registered_meta)

    def anonymize_registration_responses(self, obj):
        """
        For any questions that have a `contributor-input` block type, delete
        that question's response from registration_responses.

        We want to make sure author's names that need to be anonymized
        aren't surfaced when viewed through an anonymous VOL
        """
        return self.anonymize_fields(obj, obj.registration_responses)

    def anonymize_fields(self, obj, data):
        """
        Consolidates logic to anonymize fields with contributor information
        on both registered_meta and registration_responses
        """
        if is_anonymized(self.context['request']):
            anonymous_registration_response_keys = obj.get_contributor_registration_response_keys()

            for key in anonymous_registration_response_keys:
                if key in data:
                    del data[key]

        return data

    def check_admin_perms(self, registration, user, validated_data):
        """
        While admin/write users can make both make modifications to registrations,
        most fields are restricted to admin-only edits.  You must be an admin
        contributor on the registration; you cannot have gotten your admin
        permissions through group membership.

        Add fields that need admin perms to admin_only_editable_fields
        """
        user_is_admin = registration.is_admin_contributor(user)
        for field in validated_data:
            if field in self.admin_only_editable_fields and not user_is_admin:
                raise exceptions.PermissionDenied()

    def update_registration_tags(self, registration, validated_data, auth):
        new_tags = validated_data.pop('tags', [])
        try:
            registration.update_tags(new_tags, auth=auth)
        except NodeStateError as err:
            raise Conflict(str(err))

    def retract_registration(self, registration, validated_data, user):
        is_pending_retraction = validated_data.pop('is_pending_retraction', None)
        withdrawal_justification = validated_data.pop('withdrawal_justification', None)
        if withdrawal_justification and not is_pending_retraction:
            raise exceptions.ValidationError(
                'You cannot provide a withdrawal_justification without a concurrent withdrawal request.',
            )
        if is_truthy(is_pending_retraction):
            if registration.is_pending_retraction:
                raise exceptions.ValidationError('This registration is already pending withdrawal.')
            try:
                retraction = registration.retract_registration(user, withdrawal_justification, save=True)
            except NodeStateError as err:
                raise exceptions.ValidationError(str(err))
            retraction.ask(registration.get_active_contributors_recursive(unique_users=True))
        elif is_pending_retraction is not None:
            raise exceptions.ValidationError('You cannot set is_pending_withdrawal to False.')

    def update(self, registration, validated_data):
        user = self.context['request'].user
        auth = Auth(user)
        self.check_admin_perms(registration, user, validated_data)
        validated_data.pop('_id', None)

        if 'tags' in validated_data:
            self.update_registration_tags(registration, validated_data, auth)
        if 'custom_citation' in validated_data:
            registration.update_custom_citation(validated_data.pop('custom_citation'), auth)
        if 'license_type' in validated_data or 'license' in validated_data:
            license_details = get_license_details(registration, validated_data)
            validated_data['node_license'] = license_details
            validated_data.pop('license_type', None)
            validated_data.pop('license', None)
        if 'affiliated_institutions' in validated_data:
            institutions_list = validated_data.pop('affiliated_institutions')
            new_institutions = [{'_id': institution} for institution in institutions_list]
            update_institutions(registration, new_institutions, user)
            registration.save()
        if 'subjects' in validated_data:
            subjects = validated_data.pop('subjects', None)
            self.update_subjects(registration, subjects, auth)
        if 'withdrawal_justification' in validated_data or 'is_pending_retraction' in validated_data:
            self.retract_registration(registration, validated_data, user)
        if 'is_public' in validated_data:
            if validated_data.get('is_public') is False:
                raise exceptions.ValidationError('Registrations can only be turned from private to public.')

        try:
            registration.update(validated_data, auth=auth)
        except ValidationError as e:
            raise InvalidModelValueError(detail=e.messages[0])
        except NodeUpdateError as err:
            raise exceptions.ValidationError(err.reason)
        except NodeStateError as err:
            raise exceptions.ValidationError(str(err))

        return registration

    class Meta:
        type_ = 'registrations'


class RegistrationCreateSerializer(RegistrationSerializer):
    """
    Overrides RegistrationSerializer to add draft_registration, registration_choice, and lift_embargo fields -
    """

    def expect_cleaner_attributes(self, request):
        return StrictVersion(getattr(request, 'version', '2.0')) >= StrictVersion(CREATE_REGISTRATION_FIELD_CHANGE_VERSION)

    def __init__(self, *args, **kwargs):
        super(RegistrationCreateSerializer, self).__init__(*args, **kwargs)
        request = kwargs['context']['request']
        # required fields defined here for the different versions
        if self.expect_cleaner_attributes(request):
            self.fields['draft_registration_id'] = ser.CharField(write_only=True)
        else:
            self.fields['draft_registration'] = ser.CharField(write_only=True)

    # For newer versions
    embargo_end_date = VersionedDateTimeField(write_only=True, allow_null=True, default=None)
    included_node_ids = ser.ListField(write_only=True, required=False)
    # For older versions
    lift_embargo = VersionedDateTimeField(write_only=True, default=None, input_formats=['%Y-%m-%dT%H:%M:%S'])
    children = ser.ListField(write_only=True, required=False)
    registration_choice = ser.ChoiceField(write_only=True, required=False, choices=['immediate', 'embargo'])

    users = RelationshipField(
        related_view='users:user-detail',
        related_view_kwargs={'user_id': '<user._id>'},
        always_embed=True,
        required=False,
    )

    def get_registration_choice_by_version(self, validated_data):
        """
        Old API versions should pass in "immediate" or "embargo" under `registration_choice`.
        New API versions should pass in an "embargo_end_date" if it should be embargoed, else it will be None
        """
        if self.expect_cleaner_attributes(self.context['request']):
            if validated_data.get('registration_choice'):
                raise JSONAPIException(
                    source={'pointer': '/data/attributes/registration_choice'},
                    detail=f'Deprecated in version {CREATE_REGISTRATION_FIELD_CHANGE_VERSION}. Use embargo_end_date instead.',
                )
            return 'embargo' if validated_data.get('embargo_end_date', None) else 'immediate'
        return validated_data.get('registration_choice', 'immediate')

    def get_embargo_end_date_by_version(self, validated_data):
        """
        Old API versions should pass in "lift_embargo".
        New API versions should pass in "embargo_end_date"
        """
        if self.expect_cleaner_attributes(self.context['request']):
            if validated_data.get('lift_embargo'):
                raise JSONAPIException(
                    source={'pointer': '/data/attributes/lift_embargo'},
                    detail=f'Deprecated in version {CREATE_REGISTRATION_FIELD_CHANGE_VERSION}. Use embargo_end_date instead.',
                )
            return validated_data.get('embargo_end_date', None)
        return validated_data.get('lift_embargo')

    def get_children_by_version(self, validated_data):
        """
        Old API versions should pass in 'children'
        New API versions should pass in 'included_node_ids'.
        """
        if self.expect_cleaner_attributes(self.context['request']):
            return validated_data.get('included_node_ids', [])
        return validated_data.get('children', [])

    def create(self, validated_data):
        auth = get_user_auth(self.context['request'])
        draft = validated_data.pop('draft', None)
        registration_choice = self.get_registration_choice_by_version(validated_data)
        embargo_lifted = self.get_embargo_end_date_by_version(validated_data)

        children = self.get_children_by_version(validated_data)
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
                                             ' registered: {}'.format(', '.join(orphan_files_names)))

        try:
            # Still validating metadata, but whether `registration_responses` or `registration_metadata` were populated
            # on the draft, the other field was built and populated as well.  Both should exist.
            draft.validate_metadata(metadata=draft.registration_metadata, required_fields=True)
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
        for key, value in files.items():
            if 'extra' in value:
                for file_metadata in value['extra']:
                    if not self._is_attached_file_valid(file_metadata, registering):
                        orphan_files.append(file_metadata)

        return orphan_files

    def _is_attached_file_valid(self, file_metadata, registering):
        """
        Validation of file information on registration_metadata.  Theoretically, the file information
        on registration_responses does not have to be valid, so we enforce their accuracy here,
        to ensure file links load properly.

        Verifying that nodeId in the file_metadata is one of the files we're registering. Verify
        that selectedFileName is the name of a file on the node.  Verify that the sha256 matches
        a version on that file.

        :param file_metadata - under "registration_metadata"
        :param registering - node ids you are registering
        :return boolean
        """

        node_id = file_metadata.get('nodeId')
        if node_id not in registering:
            return False

        node = AbstractNode.load(node_id)
        if not node:
            # node in registration_metadata doesn't exist
            return False

        specified_sha = file_metadata.get('sha256', '')

        file = node.files.filter(name=normalize('NFD', file_metadata.get('selectedFileName', ''))).first() or \
               node.files.filter(name=normalize('NFC', file_metadata.get('selectedFileName', ''))).first()
        if not file:
            # file with this name does not exist on the node
            return False

        match = False
        for version in file.versions.all():
            if specified_sha == version.metadata.get('sha256'):
                match = True

        if not match:
            # Specified sha256 does not match a version on the specified file
            return False

        return True


class RegistrationDetailSerializer(RegistrationSerializer):
    """
    Overrides RegistrationSerializer make _id required and other fields writeable
    """

    id = IDField(source='_id', required=True)

    pending_withdrawal = HideIfWithdrawal(ser.BooleanField(
        source='is_pending_retraction', required=False,
        help_text='The registration is awaiting withdrawal approval by project admins.',
    ))
    withdrawal_justification = ser.CharField(required=False)


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

    comments = FileRelationshipField(
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
