from django.core.exceptions import ValidationError
from rest_framework import exceptions
from rest_framework import serializers as ser
from rest_framework.fields import empty
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError as DRFValidationError

from api.base.exceptions import Conflict, JSONAPIException
from api.base.serializers import (
    BaseAPISerializer,
    JSONAPISerializer,
    IDField,
    TypeField,
    HideIfNotWithdrawal,
    NoneIfWithdrawal,
    LinksField,
    RelationshipField,
    VersionedDateTimeField,
    JSONAPIListField,
    NodeFileHyperLinkField,
    WaterbutlerLink,
    HideIfPreprint,
    LinkedNodesRelationshipSerializer,
)
from api.base.utils import absolute_reverse, get_user_auth
from api.base.parsers import NO_DATA_ERROR
from api.nodes.serializers import (
    NodeCitationSerializer,
    NodeLicenseRelationshipField,
    NodeLicenseSerializer,
    NodeContributorsSerializer,
    NodeStorageProviderSerializer,
    NodeContributorsCreateSerializer,
    NodeContributorDetailSerializer,
    get_license_details,
    NodeTagField,
)
from api.base.metrics import MetricsSerializerMixin
from api.institutions.utils import update_institutions_if_user_associated
from api.preprints.fields import DOIField
from api.taxonomies.serializers import TaxonomizableSerializerMixin
from api.waffle.utils import flag_is_active
from framework.exceptions import PermissionsError, UnpublishedPendingPreprintVersionExists
from website.project import signals as project_signals
from osf.exceptions import NodeStateError, PreprintStateError
from osf.models import (
    BaseFileNode,
    Preprint,
    PreprintProvider,
    Node,
    NodeLicense,
)
from osf.utils import permissions as osf_permissions
from osf.utils.workflows import DefaultStates


class PrimaryFileRelationshipField(RelationshipField):
    def get_object(self, file_id):
        return BaseFileNode.load(file_id)

    def to_internal_value(self, data):
        return self.get_object(data)


class NodeRelationshipField(RelationshipField):
    def get_object(self, node_id):
        try:
            return Node.load(node_id)
        except AttributeError:
            raise exceptions.ValidationError(detail='Node not correctly specified.')

    def to_internal_value(self, data):
        return self.get_object(data)


class PreprintProviderRelationshipField(RelationshipField):
    def get_object(self, node_id):
        return PreprintProvider.load(node_id)

    def to_internal_value(self, data):
        return self.get_object(data)


class PreprintLicenseRelationshipField(RelationshipField):
    def to_internal_value(self, license_id):
        license = NodeLicense.load(license_id)
        if license:
            return license
        raise exceptions.NotFound('Unable to find specified license.')


class PreprintSerializer(TaxonomizableSerializerMixin, MetricsSerializerMixin, JSONAPISerializer):
    filterable_fields = frozenset([
        'id',
        'date_created',
        'date_modified',
        'date_published',
        'original_publication_date',
        'provider',
        'is_published',
        'subjects',
        'reviews_state',
        'node_is_public',
    ])
    available_metrics = frozenset([
        'downloads',
        'views',
    ])

    id = IDField(source='_id', read_only=True)
    type = TypeField()

    date_created = VersionedDateTimeField(source='created', read_only=True)
    date_modified = VersionedDateTimeField(source='modified', read_only=True)
    date_published = VersionedDateTimeField(read_only=True)
    original_publication_date = VersionedDateTimeField(required=False, allow_null=True)
    custom_publication_citation = ser.CharField(required=False, allow_blank=True, allow_null=True)
    doi = DOIField(source='article_doi', required=False, allow_null=True, allow_blank=True)
    title = ser.CharField(required=True, max_length=512)
    description = ser.CharField(required=False, allow_blank=True, allow_null=True)
    is_published = NoneIfWithdrawal(ser.BooleanField(required=False))
    is_preprint_orphan = NoneIfWithdrawal(ser.BooleanField(read_only=True))
    license_record = NodeLicenseSerializer(required=False, source='license')
    tags = JSONAPIListField(child=NodeTagField(), required=False)
    node_is_public = ser.BooleanField(
        read_only=True, source='node__is_public',
        help_text='Is supplementary project public?',
    )
    preprint_doi_created = NoneIfWithdrawal(VersionedDateTimeField(read_only=True))
    date_withdrawn = VersionedDateTimeField(read_only=True, allow_null=True)
    withdrawal_justification = HideIfNotWithdrawal(ser.CharField(required=False, read_only=True, allow_blank=True))

    current_user_permissions = ser.SerializerMethodField(
        help_text='List of strings representing the permissions '
                  'for the current user on this preprint.',
    )
    public = ser.BooleanField(source='is_public', required=False, read_only=True)
    contributors = RelationshipField(
        related_view='preprints:preprint-contributors',
        related_view_kwargs={'preprint_id': '<_id>'},
    )
    bibliographic_contributors = RelationshipField(
        related_view='preprints:preprint-bibliographic-contributors',
        related_view_kwargs={'preprint_id': '<_id>'},
    )
    reviews_state = ser.CharField(source='machine_state', read_only=True, max_length=15)
    date_last_transitioned = NoneIfWithdrawal(VersionedDateTimeField(read_only=True))
    version = ser.IntegerField(read_only=True)
    is_latest_version = ser.BooleanField(read_only=True)

    versions = RelationshipField(
        related_view='preprints:preprint-versions',
        related_view_kwargs={'preprint_id': '<_id>'},
        read_only=True,
    )

    citation = NoneIfWithdrawal(
        RelationshipField(
            related_view='preprints:preprint-citation',
            related_view_kwargs={'preprint_id': '<_id>'},
        ),
    )

    identifiers = NoneIfWithdrawal(
        RelationshipField(
            related_view='preprints:identifier-list',
            related_view_kwargs={'preprint_id': '<_id>'},
        ),
    )

    node = NoneIfWithdrawal(
        NodeRelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<node._id>'},
            read_only=False,
            self_view='preprints:preprint-node-relationship',
            self_view_kwargs={'preprint_id': '<_id>'},
        ),
    )

    license = NodeLicenseRelationshipField(
        related_view='licenses:license-detail',
        related_view_kwargs={'license_id': '<license.node_license._id>'},
        read_only=False,
    )

    provider = PreprintProviderRelationshipField(
        related_view='providers:preprint-providers:preprint-provider-detail',
        related_view_kwargs={'provider_id': '<provider._id>'},
        read_only=False,
    )

    files = NoneIfWithdrawal(
        RelationshipField(
            related_view='preprints:preprint-storage-providers',
            related_view_kwargs={'preprint_id': '<_id>'},
        ),
    )

    primary_file = NoneIfWithdrawal(
        PrimaryFileRelationshipField(
            related_view='files:file-detail',
            related_view_kwargs={'file_id': '<primary_file._id>'},
            read_only=False,
        ),
    )

    review_actions = RelationshipField(
        related_view='preprints:preprint-review-action-list',
        related_view_kwargs={'preprint_id': '<_id>'},
    )

    requests = NoneIfWithdrawal(
        RelationshipField(
            related_view='preprints:preprint-request-list',
            related_view_kwargs={'preprint_id': '<_id>'},
        ),
    )

    affiliated_institutions = RelationshipField(
        related_view='preprints:preprints-institutions',
        related_view_kwargs={'preprint_id': '<_id>'},
        self_view='preprints:preprint-relationships-institutions',
        self_view_kwargs={'preprint_id': '<_id>'},
        read_only=False,
        required=False,
        allow_null=True,
    )

    links = LinksField(
        {
            'self': 'get_preprint_url',
            'html': 'get_absolute_html_url',
            'doi': 'get_article_doi_url',
            'preprint_doi': 'get_preprint_doi_url',
        },
    )

    has_coi = ser.BooleanField(required=False, allow_null=True)
    conflict_of_interest_statement = ser.CharField(required=False, allow_blank=True, allow_null=True)
    has_data_links = ser.ChoiceField(Preprint.HAS_LINKS_CHOICES, required=False)
    why_no_data = ser.CharField(required=False, allow_blank=True, allow_null=True)
    data_links = ser.ListField(child=ser.URLField(), required=False)
    has_prereg_links = ser.ChoiceField(Preprint.HAS_LINKS_CHOICES, required=False)
    why_no_prereg = ser.CharField(required=False, allow_blank=True, allow_null=True)
    prereg_links = ser.ListField(child=ser.URLField(), required=False)
    prereg_link_info = ser.ChoiceField(Preprint.PREREG_LINK_INFO_CHOICES, required=False, allow_blank=True)

    class Meta:
        type_ = 'preprints'

    @property
    def subjects_related_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'preprints:preprint-subjects'

    @property
    def subjects_view_kwargs(self):
        # Overrides TaxonomizableSerializerMixin
        return {'preprint_id': '<_id>'}

    @property
    def subjects_self_view(self):
        # Overrides TaxonomizableSerializerMixin
        return 'preprints:preprint-relationships-subjects'

    def get_preprint_url(self, obj):
        return absolute_reverse(
            'preprints:preprint-detail',
            kwargs={
                'preprint_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    def get_absolute_url(self, obj):
        return self.get_preprint_url(obj)

    def get_article_doi_url(self, obj):
        return f'https://doi.org/{obj.article_doi}' if obj.article_doi else None

    def get_current_user_permissions(self, obj):
        user = self.context['request'].user
        return obj.get_permissions(user)[::-1]

    def get_preprint_doi_url(self, obj):
        doi = None
        doi_identifier = obj.get_identifier('doi')
        if doi_identifier:
            doi = doi_identifier.value
        # if a preprint hasn't been published yet, don't show the DOI prematurely
        elif obj.is_published:
            client = obj.get_doi_client()
            doi = client.build_doi(preprint=obj) if client else None
        return f'https://doi.org/{doi}' if doi else None

    def update(self, preprint, validated_data):
        assert isinstance(preprint, Preprint), 'You must specify a valid preprint to be updated'

        auth = get_user_auth(self.context['request'])
        ignore_permission = self.context.get('ignore_permission', False)
        if not ignore_permission and not preprint.has_permission(auth.user, osf_permissions.WRITE):
            raise exceptions.PermissionDenied(detail='User must have admin or write permissions to update a preprint.')

        for field in ['conflict_of_interest_statement', 'why_no_data', 'why_no_prereg']:
            if field in validated_data:
                value = validated_data[field]
                if isinstance(value, str) and not value.strip():
                    validated_data[field] = None

        updated_has_coi = validated_data.get('has_coi', preprint.has_coi)
        updated_conflict_statement = validated_data.get('conflict_of_interest_statement', preprint.conflict_of_interest_statement)

        updated_has_data_links = validated_data.get('has_data_links', preprint.has_data_links)
        updated_why_no_data = validated_data.get('why_no_data', preprint.why_no_data)

        updated_has_prereg_links = validated_data.get('has_prereg_links', preprint.has_prereg_links)
        updated_why_no_prereg = validated_data.get('why_no_prereg', preprint.why_no_prereg)

        if updated_has_coi is False and updated_conflict_statement:
            raise exceptions.ValidationError(
                detail='Cannot provide conflict of interest statement when has_coi is set to False.',
            )

        if updated_has_data_links != 'no' and updated_why_no_data:
            raise exceptions.ValidationError(
                detail='You cannot edit this statement while your data links availability is set to true or is unanswered.',
            )

        if updated_has_data_links == 'no' and 'data_links' in validated_data and validated_data['data_links']:
            raise exceptions.ValidationError(
                detail='Cannot provide data links when has_data_links is set to "no".',
            )

        if updated_has_prereg_links != 'no' and updated_why_no_prereg:
            raise exceptions.ValidationError(
                detail='You cannot edit this statement while your prereg links availability is set to true or is unanswered.',
            )

        if updated_has_prereg_links != 'available':
            if 'prereg_links' in validated_data and validated_data['prereg_links']:
                raise exceptions.ValidationError(
                    detail='You cannot edit this field while your prereg links availability is set to false or is unanswered.',
                )
            if 'prereg_link_info' in validated_data and validated_data['prereg_link_info']:
                raise exceptions.ValidationError(
                    detail='You cannot edit this field while your prereg links availability is set to false or is unanswered.',
                )

        try:
            if 'has_coi' in validated_data:
                preprint.update_has_coi(auth, validated_data['has_coi'], ignore_permission=ignore_permission)

            if 'conflict_of_interest_statement' in validated_data:
                preprint.update_conflict_of_interest_statement(auth, validated_data['conflict_of_interest_statement'], ignore_permission=ignore_permission)

            if 'has_data_links' in validated_data:
                preprint.update_has_data_links(auth, validated_data['has_data_links'], ignore_permission=ignore_permission)

            if 'why_no_data' in validated_data:
                preprint.update_why_no_data(auth, validated_data['why_no_data'], ignore_permission=ignore_permission)

            if 'has_prereg_links' in validated_data:
                preprint.update_has_prereg_links(auth, validated_data['has_prereg_links'], ignore_permission=ignore_permission)

            if 'why_no_prereg' in validated_data:
                preprint.update_why_no_prereg(auth, validated_data['why_no_prereg'], ignore_permission=ignore_permission)

            if 'prereg_links' in validated_data:
                preprint.update_prereg_links(auth, validated_data['prereg_links'], ignore_permission=ignore_permission)

            if 'prereg_link_info' in validated_data:
                preprint.update_prereg_link_info(auth, validated_data['prereg_link_info'], ignore_permission=ignore_permission)

            if 'data_links' in validated_data:
                preprint.update_data_links(auth, validated_data['data_links'], ignore_permission=ignore_permission)
            else:
                if updated_has_data_links == 'no' and preprint.data_links:
                    preprint.update_data_links(auth, [], ignore_permission=ignore_permission)
        except PreprintStateError as e:
            raise exceptions.ValidationError(detail=str(e))
        except PermissionsError:
            raise exceptions.PermissionDenied(detail='Must have admin permissions to update author assertion fields.')

        published = validated_data.pop('is_published', None)
        if published and preprint.provider.is_reviewed:
            url = absolute_reverse(
                'preprints:preprint-review-action-list',
                kwargs={
                    'version': self.context['request'].parser_context['kwargs']['version'],
                    'preprint_id': preprint._id,
                },
            )
            raise Conflict(
                f'{preprint.provider.name} uses a moderation workflow, so preprints must be submitted '
                'for review instead of published directly. '
                f'Submit a preprint by creating a `submit` Action at {url}',
            )

        recently_published = False

        primary_file = validated_data.pop('primary_file', None)
        if primary_file:
            self.set_field(preprint.set_primary_file, primary_file, auth, ignore_permission=ignore_permission)

        old_tags = set(preprint.tags.values_list('name', flat=True))
        if 'tags' in validated_data:
            current_tags = set(validated_data.pop('tags', []))
        elif self.partial:
            current_tags = set(old_tags)
        else:
            current_tags = set()

        for new_tag in (current_tags - old_tags):
            preprint.add_tag(new_tag, auth=auth)
        for deleted_tag in (old_tags - current_tags):
            preprint.remove_tag(deleted_tag, auth=auth)

        if 'node' in validated_data:
            node = validated_data.pop('node', None)
            self.set_field(preprint.set_supplemental_node, node, auth, ignore_node_permissions=ignore_permission, ignore_permission=ignore_permission)

        if 'subjects' in validated_data:
            subjects = validated_data.pop('subjects', None)
            self.update_subjects(preprint, subjects, auth)

        if 'title' in validated_data:
            title = validated_data['title']
            self.set_field(preprint.set_title, title, auth, ignore_permission=ignore_permission)

        if 'description' in validated_data:
            description = validated_data['description']
            self.set_field(preprint.set_description, description, auth, ignore_permission=ignore_permission)

        if 'article_doi' in validated_data:
            preprint.article_doi = validated_data['article_doi']

        if 'license_type' in validated_data or 'license' in validated_data:
            license_details = get_license_details(preprint, validated_data)
            self.set_field(preprint.set_preprint_license, license_details, auth, ignore_permission=ignore_permission)

        if 'original_publication_date' in validated_data:
            preprint.original_publication_date = validated_data['original_publication_date'] or None

        if 'custom_publication_citation' in validated_data:
            preprint.custom_publication_citation = validated_data['custom_publication_citation'] or None

        if published is not None:
            if not preprint.primary_file:
                raise exceptions.ValidationError(
                    detail='A valid primary_file must be set before publishing a preprint.',
                )
            self.set_field(preprint.set_published, published, auth, ignore_permission=ignore_permission)
            recently_published = published
            preprint.set_privacy('public', log=False, save=True, ignore_permission=ignore_permission)

        try:
            preprint.full_clean()
        except ValidationError as e:
            raise exceptions.ValidationError(detail=str(e))

        preprint.save()

        if recently_published:
            for author in preprint.contributors:
                if author != auth.user:
                    project_signals.contributor_added.send(
                        preprint,
                        contributor=author,
                        auth=auth,
                        email_template='preprint',
                    )

        return preprint

    def set_field(self, func, val, auth, **kwargs):
        try:
            func(val, auth, **kwargs)
        except PermissionsError as e:
            raise exceptions.PermissionDenied(detail=str(e))
        except (ValueError, ValidationError, NodeStateError) as e:
            raise exceptions.ValidationError(detail=str(e))


class PreprintDraftSerializer(PreprintSerializer):

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'users:user-draft-preprints',
            kwargs={
                'preprint_id': obj._id,
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )

    class Meta:
        type_ = 'draft-preprints'


class PreprintCreateSerializer(PreprintSerializer):
    # Overrides PreprintSerializer to make id nullable, adds `create`
    # TODO: add better Docstrings
    id = IDField(source='_id', required=False, allow_null=True)
    doi = ser.CharField(write_only=True, required=False)

    def create(self, validated_data):
        creator = self.context['request'].user
        provider = validated_data.pop('provider', None)
        if not provider:
            raise exceptions.ValidationError(detail='You must specify a valid provider to create a preprint.')

        title = validated_data.pop('title')
        description = validated_data.pop('description', '')
        doi = validated_data.pop('doi') if flag_is_active(self.context['request'], 'doi_setter') else None

        preprint = Preprint.create(provider=provider, title=title, creator=creator, description=description, doi=doi)

        return self.update(preprint, validated_data)


class PreprintCreateVersionSerializer(PreprintSerializer):
    # Overrides PreprintSerializer to make title nullable and customize version creation
    # TODO: add better Docstrings
    id = IDField(source='_id', required=False, allow_null=True)
    title = ser.CharField(required=False)
    create_from_guid = ser.CharField(required=True, write_only=True)

    def create(self, validated_data):
        create_from_guid = validated_data.pop('create_from_guid', None)
        auth = get_user_auth(self.context['request'])
        try:
            preprint, data_to_update = Preprint.create_version(create_from_guid, auth)
        except PermissionsError:
            raise PermissionDenied(detail='User must have ADMIN permission to create a new preprint version.')
        except UnpublishedPendingPreprintVersionExists:
            raise Conflict(detail='Failed to create a new preprint version due to unpublished pending version exists.')
        if not preprint:
            raise NotFound(detail='Failed to create a new preprint version due to source preprint not found.')
        for contributor in preprint.contributor_set.filter(user__is_registered=False):
            contributor.user.add_unclaimed_record(
                claim_origin=preprint,
                referrer=auth.user,
                email=contributor.user.email,
                given_name=contributor.user.fullname,
            )
        if data_to_update:
            return self.update(preprint, data_to_update)
        return preprint


class PreprintCitationSerializer(NodeCitationSerializer):
    class Meta:
        type_ = 'preprint-citation'


class PreprintContributorsSerializer(NodeContributorsSerializer):
    """ Separate from UserSerializer due to necessity to override almost every field as read only
    """
    preprint = RelationshipField(
        related_view='preprints:preprint-detail',
        related_view_kwargs={'preprint_id': '<preprint._id>'},
    )

    node = HideIfPreprint(
        RelationshipField(
            related_view='nodes:node-detail',
            related_view_kwargs={'node_id': '<node._id>'},
        ),
    )

    class Meta:
        type_ = 'contributors'

    def get_absolute_url(self, obj):
        return absolute_reverse(
            'preprints:preprint-contributor-detail',
            kwargs={
                'user_id': obj.user._id,
                'preprint_id': self.context['request'].parser_context['kwargs']['preprint_id'],
                'version': self.context['request'].parser_context['kwargs']['version'],
            },
        )


class PreprintContributorsCreateSerializer(NodeContributorsCreateSerializer, PreprintContributorsSerializer):
    """
    Overrides PreprintContributorsSerializer to add email, full_name, send_email, and non-required index and users field.

    id and index redefined because of the two serializers we've inherited
    """
    id = IDField(source='_id', required=False, allow_null=True)
    index = ser.IntegerField(required=False, source='_order')

    email_preferences = ['preprint', 'false']


class PreprintContributorDetailSerializer(NodeContributorDetailSerializer, PreprintContributorsSerializer):
    """
    Overrides NodeContributorDetailSerializer to set the preprint instead of the node

    id and index redefined because of the two serializers we've inherited
    """
    id = IDField(required=True, source='_id')
    index = ser.IntegerField(required=False, read_only=False, source='_order')

    def validate_permission(self, value):
        preprint = self.context.get('resource')
        user = self.context.get('user')
        if (
            user  # if user is None then probably we're trying to make bulk update and this validation is not relevant
            and preprint.machine_state == DefaultStates.INITIAL.value
            and preprint.creator_id == user.id
        ):
            raise ValidationError(
                'You cannot change your permission setting at this time. '
                'Have another admin contributor edit your permission after you’ve submitted your preprint',
            )
        return value


class PreprintStorageProviderSerializer(NodeStorageProviderSerializer):
    node = HideIfPreprint(ser.CharField(source='node_id', read_only=True))
    preprint = ser.CharField(source='node_id', read_only=True)

    files = NodeFileHyperLinkField(
        related_view='preprints:preprint-files',
        related_view_kwargs={'preprint_id': '<node._id>'},
        kind='folder',
        never_embed=True,
    )

    links = LinksField({
        'upload': WaterbutlerLink(),
    })


class PreprintNodeRelationshipSerializer(LinkedNodesRelationshipSerializer):
    data = ser.DictField()

    def run_validation(self, data=empty):
        """
        Overwrites run_validation.
        JSONAPIOnetoOneRelationshipParser parses data into {id: None, type: None} if data is null,
        which is what this endpoint expects.
        """

        if data == {}:
            raise JSONAPIException(source={'pointer': '/data'}, detail=NO_DATA_ERROR)

        if data.get('type', None) is not None and data.get('id', None) is not None:
            raise DRFValidationError(
                {'data': 'Data must be null. This endpoint can only be used to unset the supplemental project.'},
                400,
            )
        return data

    def make_instance_obj(self, obj):
        # Convenience method to format instance based on view's get_object
        return {
            'data': None,
            'self': obj,
        }

    def update(self, instance, validated_data):
        auth = get_user_auth(self.context['request'])
        preprint = instance['self']
        preprint.unset_supplemental_node(auth=auth)
        preprint.save()
        return self.make_instance_obj(preprint)

    links = LinksField({
        'self': 'get_self_url',
    })


class PreprintsInstitutionsRelationshipSerializer(BaseAPISerializer):
    from api.institutions.serializers import InstitutionRelated  # Avoid circular import
    data = ser.ListField(child=InstitutionRelated())

    links = LinksField({
        'self': 'get_self_url',
    })

    def get_self_url(self, obj):
        return obj['self'].institutions_relationship_url

    class Meta:
        type_ = 'institutions'

    def make_instance_obj(self, obj):
        return {
            'data': obj.affiliated_institutions.all(),
            'self': obj,
        }

    def update(self, instance, validated_data):
        preprint = instance['self']
        user = self.context['request'].user
        update_institutions_if_user_associated(preprint, validated_data['data'], user)
        preprint.save()
        return self.make_instance_obj(preprint)

    def create(self, validated_data):
        instance = self.context['view'].get_object()
        preprint = instance['self']
        user = self.context['request'].user
        update_institutions_if_user_associated(preprint, validated_data['data'], user)
        preprint.save()
        return self.make_instance_obj(preprint)
