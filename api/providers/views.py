from django.db.models import Case, CharField, Q, Value, When, IntegerField
from guardian.shortcuts import get_objects_for_user
from rest_framework.exceptions import ValidationError
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotAuthenticated, NotFound

from api.actions.serializers import RegistrationActionSerializer
from api.base import permissions as base_permissions
from osf.models.action import RegistrationAction
from api.base.exceptions import InvalidFilterValue, InvalidFilterOperator, Conflict
from api.base.filters import PreprintFilterMixin, ListFilterMixin
from api.base.views import JSONAPIBaseView, DeprecatedView
from api.base.metrics import MetricsViewMixin
from api.base.pagination import MaxSizePagination, IncreasedPageSizePagination
from api.base.utils import get_object_or_error, get_user_auth, is_truthy
from api.licenses.views import LicenseList
from api.collections.permissions import CanSubmitToCollectionOrPublic
from api.collections.serializers import CollectionSubmissionSerializer, CollectionSubmissionCreateSerializer
from api.registrations.serializers import RegistrationSerializer
from api.requests.serializers import PreprintRequestSerializer, RegistrationRequestSerializer
from api.preprints.permissions import PreprintPublishedOrAdmin
from api.preprints.serializers import PreprintSerializer
from api.providers.permissions import CanAddModerator, CanDeleteModerator, CanUpdateModerator, CanSetUpProvider, MustBeModerator
from api.providers.serializers import (
    CollectionProviderSerializer,
    PreprintProviderSerializer,
    PreprintModeratorSerializer,
    RegistrationProviderSerializer,
    RegistrationModeratorSerializer,
)
from api.schemas.serializers import RegistrationSchemaSerializer
from api.subjects.views import SubjectList
from api.subjects.serializers import SubjectSerializer
from api.taxonomies.serializers import TaxonomySerializer
from api.taxonomies.utils import optimize_subject_query
from framework.auth.oauth_scopes import CoreScopes

from osf.models import (
    AbstractNode,
    CollectionProvider,
    CollectionSubmission,
    NodeLicense,
    OSFUser,
    RegistrationProvider,
    Subject,
    PreprintRequest,
    PreprintProvider,
    WhitelistedSHAREPreprintProvider,
    NodeRequest,
    Registration,
)
from osf.utils.permissions import REVIEW_PERMISSIONS, ADMIN
from osf.utils.workflows import RequestTypes
from osf.metrics import PreprintDownload, PreprintView


class ProviderMixin:

    provider_class = None

    def get_provider(self):
        # used in perms class
        assert self.provider_class is not None, 'must define provider class to use ProviderMixin'

        if self.kwargs.get('provider_id'):
            return get_object_or_error(
                self.provider_class,
                self.kwargs['provider_id'],
                self.request,
                display_name=self.provider_class.__name__,
            )

        if self.kwargs.get('node_id'):
            return get_object_or_error(
                AbstractNode,
                self.kwargs['node_id'],
                self.request,
                display_name=AbstractNode.__name__,
            ).provider


class GenericProviderList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    pagination_class = MaxSizePagination
    ordering = ('name', )

    def get_default_queryset(self):
        return self.model_class.objects.all()

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()


class CollectionProviderList(GenericProviderList):
    model_class = CollectionProvider
    serializer_class = CollectionProviderSerializer
    view_category = 'collection-providers'
    view_name = 'collection-providers-list'


class RegistrationProviderList(GenericProviderList):
    model_class = RegistrationProvider
    serializer_class = RegistrationProviderSerializer
    view_category = 'registration-providers'
    view_name = 'registration-providers-list'


class PreprintProviderList(MetricsViewMixin, GenericProviderList):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprint_provider_list).
    """

    model_class = PreprintProvider
    serializer_class = PreprintProviderSerializer
    view_category = 'preprint-providers'
    view_name = 'preprint-providers-list'
    metric_map = {
        'downloads': PreprintDownload,
        'views': PreprintView,
    }

    # overrides MetricsViewMixin
    def get_annotated_queryset_with_metrics(self, queryset, metric_class, metric_name, after):
        return metric_class.get_top_by_count(
            qs=queryset,
            model_field='_id',
            metric_field='provider_id',
            annotation=metric_name,
            after=after,
            size=None,
        )

    def get_renderer_context(self):
        context = super(PreprintProviderList, self).get_renderer_context()
        context['meta'] = {
            'whitelisted_providers': WhitelistedSHAREPreprintProvider.objects.all().values_list('provider_name', flat=True),
        }
        return context

    def build_query_from_field(self, field_name, operation):
        if field_name == 'permissions':
            if operation['op'] != 'eq':
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq'])
            auth = get_user_auth(self.request)
            auth_user = getattr(auth, 'user', None)
            if not auth_user:
                raise NotAuthenticated()
            value = operation['value'].lstrip('[').rstrip(']')
            permissions = [v.strip() for v in value.split(',')]
            perm_options = [perm[0] for perm in REVIEW_PERMISSIONS]
            if not set(permissions).issubset(set(perm_options)):
                valid_permissions = ', '.join(perm_options)
                raise InvalidFilterValue('Invalid permission! Valid values are: {}'.format(valid_permissions))
            return Q(id__in=get_objects_for_user(auth_user, permissions, PreprintProvider, any_perm=True))

        return super(PreprintProviderList, self).build_query_from_field(field_name, operation)


class GenericProviderDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.PROVIDERS_WRITE]

    def get_object(self):
        provider = get_object_or_error(self.model_class, self.kwargs['provider_id'], self.request, display_name=self.model_class.__name__)
        self.check_object_permissions(self.request, provider)
        return provider

class CollectionProviderDetail(GenericProviderDetail):
    model_class = CollectionProvider
    serializer_class = CollectionProviderSerializer
    view_category = 'collection-providers'
    view_name = 'collection-provider-detail'


class RegistrationProviderDetail(GenericProviderDetail):
    model_class = RegistrationProvider
    serializer_class = RegistrationProviderSerializer
    view_category = 'registration-providers'
    view_name = 'registration-provider-detail'


class PreprintProviderDetail(GenericProviderDetail, generics.UpdateAPIView):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprint_provider_detail).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        CanSetUpProvider,
    )
    model_class = PreprintProvider
    serializer_class = PreprintProviderSerializer
    view_category = 'preprint-providers'
    view_name = 'preprint-provider-detail'

    def perform_update(self, serializer):
        if serializer.instance.is_reviewed:
            raise Conflict('Reviews settings may be set only once. Contact support@osf.io if you need to update them.')
        super(PreprintProviderDetail, self).perform_update(serializer)


class GenericProviderTaxonomies(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = TaxonomySerializer
    pagination_class = IncreasedPageSizePagination
    view_name = 'taxonomy-list'

    ordering = ('-id',)

    def get_queryset(self):
        parent = self.request.query_params.get('filter[parents]', None) or self.request.query_params.get('filter[parent]', None)
        provider = get_object_or_error(self.provider_class, self.kwargs['provider_id'], self.request, display_name=self.provider_class.__name__)
        if parent:
            if parent == 'null':
                return provider.top_level_subjects
            return optimize_subject_query(provider.all_subjects.filter(parent___id=parent))
        return optimize_subject_query(provider.all_subjects)


class CollectionProviderTaxonomies(DeprecatedView, GenericProviderTaxonomies):
    """
    To be deprecated: In favor of CollectionProviderSubjects
    """
    view_category = 'collection-providers'
    provider_class = CollectionProvider  # Not actually the model being serialized, privatize to avoid issues

    max_version = '2.14'

class RegistrationProviderTaxonomies(DeprecatedView, GenericProviderTaxonomies):
    """
    To be deprecated: In favor of RegistrationProviderSubjects
    """
    view_category = 'registration-providers'
    provider_class = RegistrationProvider  # Not actually the model being serialized, privatize to avoid issues

    max_version = '2.14'

class PreprintProviderTaxonomies(GenericProviderTaxonomies):
    """
    To be deprecated: In favor of PreprintProviderSubjects
    """
    view_category = 'preprint-providers'
    provider_class = PreprintProvider  # Not actually the model being serialized, privatize to avoid issues

    max_version = '2.14'


class BaseProviderSubjects(SubjectList):
    pagination_class = IncreasedPageSizePagination
    view_name = 'subject-list'

    def get_default_queryset(self):
        parent = self.request.query_params.get('filter[parent]', None)
        provider = get_object_or_error(self.provider_class, self.kwargs['provider_id'], self.request, display_name=self.provider_class.__name__)
        if parent:
            if parent == 'null':
                return provider.top_level_subjects
            return optimize_subject_query(provider.all_subjects.filter(parent___id=parent))
        return optimize_subject_query(provider.all_subjects)


class CollectionProviderSubjects(BaseProviderSubjects):
    view_category = 'collection-providers'
    provider_class = CollectionProvider  # Not actually the model being serialized, privatize to avoid issues


class RegistrationProviderSubjects(BaseProviderSubjects):
    view_category = 'registration-providers'
    provider_class = RegistrationProvider  # Not actually the model being serialized, privatize to avoid issues


class PreprintProviderSubjects(BaseProviderSubjects):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprint_provider_subjects_list).
    """
    view_category = 'preprint-providers'
    provider_class = PreprintProvider  # Not actually the model being serialized, privatize to avoid issues


class GenericProviderHighlightedTaxonomyList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_name = 'highlighted-taxonomy-list'

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = TaxonomySerializer

    def get_queryset(self):
        provider = get_object_or_error(self.provider_class, self.kwargs['provider_id'], self.request, display_name=self.provider_class.__name__)
        return optimize_subject_query(Subject.objects.filter(id__in=[s.id for s in provider.highlighted_subjects]).order_by('text'))


class CollectionProviderHighlightedTaxonomyList(DeprecatedView, GenericProviderHighlightedTaxonomyList):
    """
    To be deprecated: In favor of CollectionProviderHighlightedSubjectList
    """
    view_category = 'collection-providers'
    provider_class = CollectionProvider

    max_version = '2.14'


class RegistrationProviderHighlightedTaxonomyList(DeprecatedView, GenericProviderHighlightedTaxonomyList):
    """
    To be deprecated: In favor of RegistrationProviderHighlightedSubjectList
    """
    view_category = 'registration-providers'
    provider_class = RegistrationProvider

    max_version = '2.14'


class PreprintProviderHighlightedTaxonomyList(DeprecatedView, GenericProviderHighlightedTaxonomyList):
    """
    To be deprecated: In favor of PreprintProviderHighlightedSubjectList
    """
    view_category = 'preprint-providers'
    provider_class = PreprintProvider

    max_version = '2.14'


class GenericProviderHighlightedSubjectList(GenericProviderHighlightedTaxonomyList):
    view_name = 'highlighted-subject-list'
    serializer_class = SubjectSerializer


class CollectionProviderHighlightedSubjectList(GenericProviderHighlightedSubjectList):
    view_category = 'collection-providers'
    provider_class = CollectionProvider


class RegistrationProviderHighlightedSubjectList(GenericProviderHighlightedSubjectList):
    view_category = 'registration-providers'
    provider_class = RegistrationProvider


class PreprintProviderHighlightedSubjectList(GenericProviderHighlightedSubjectList):
    view_category = 'preprint-providers'
    provider_class = PreprintProvider


class GenericProviderLicenseList(LicenseList):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprint_provider_licenses_list)
    """
    ordering = ()  # TODO: should be ordered once the frontend for selecting default licenses no longer relies on order

    def get_default_queryset(self):
        """
        Returns provider.acceptable_licenses if they exist, otherwise returns all licenses.
        The provider's default_license is also included in the queryset if one exists.
        """
        provider = get_object_or_error(
            self.provider_class,
            self.kwargs['provider_id'],
            self.request,
            display_name=self.provider_class.__name__,
        )

        if provider.licenses_acceptable.count():
            licenses = provider.licenses_acceptable.get_queryset()
        else:
            licenses = NodeLicense.objects.all()

        if provider.default_license:
            licenses |= NodeLicense.objects.filter(id=provider.default_license.id)

        # Since default_license could also be in acceptable_licenses, filtering
        # this way to avoid duplicates without .distinct() usage
        return NodeLicense.objects.filter(
            Q(id__in=licenses.values_list('id', flat=True)),
        )


class CollectionProviderLicenseList(GenericProviderLicenseList):
    view_category = 'collection-providers'
    provider_class = CollectionProvider


class RegistrationProviderLicenseList(GenericProviderLicenseList):
    view_category = 'registration-providers'
    provider_class = RegistrationProvider


class PreprintProviderLicenseList(GenericProviderLicenseList):
    view_category = 'preprint-providers'
    provider_class = PreprintProvider


class PreprintProviderPreprintList(JSONAPIBaseView, generics.ListAPIView, PreprintFilterMixin, ProviderMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/preprint_providers_preprints_list).
    """
    provider_class = PreprintProvider
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        PreprintPublishedOrAdmin,
    )

    ordering = ('-created')

    serializer_class = PreprintSerializer
    model_class = AbstractNode

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'preprint-providers'
    view_name = 'preprints-list'

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)
        provider = self.get_provider()

        # Permissions on the list objects are handled by the query
        return self.preprints_queryset(provider.preprints.all(), auth_user)

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides APIView
    def get_renderer_context(self):
        context = super(PreprintProviderPreprintList, self).get_renderer_context()
        show_counts = is_truthy(self.request.query_params.get('meta[reviews_state_counts]', False))
        if show_counts:
            # TODO don't duplicate the above
            auth = get_user_auth(self.request)
            auth_user = getattr(auth, 'user', None)
            provider = self.get_provider()
            if auth_user and auth_user.has_perm('view_submissions', provider):
                context['meta'] = {
                    'reviews_state_counts': provider.get_reviewable_state_counts(),
                }
        return context

class CollectionProviderSubmissionList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, ProviderMixin):
    provider_class = CollectionProvider
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanSubmitToCollectionOrPublic,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.COLLECTED_META_READ]
    required_write_scopes = [CoreScopes.COLLECTED_META_WRITE]

    model_class = CollectionSubmission
    serializer_class = CollectionSubmissionSerializer
    view_category = 'collected-metadata'
    view_name = 'provider-collected-metadata-list'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CollectionSubmissionCreateSerializer
        else:
            return CollectionSubmissionSerializer

    def get_default_queryset(self):
        provider = self.get_provider()
        if provider and provider.primary_collection:
            return provider.primary_collection.collectionsubmission_set.all()
        return CollectionSubmission.objects.none()

    def get_queryset(self):
        return self.get_queryset_from_request()

    def perform_create(self, serializer):
        user = self.request.user
        provider = self.get_provider()
        if provider and provider.primary_collection:
            return serializer.save(creator=user, collection=provider.primary_collection)
        raise ValidationError('Provider {} has no primary collection to submit to.'.format(provider.name))


class RegistrationProviderSubmissionList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, ProviderMixin):
    provider_class = RegistrationProvider
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanSubmitToCollectionOrPublic,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.COLLECTED_META_READ]
    required_write_scopes = [CoreScopes.COLLECTED_META_WRITE]

    model_class = CollectionSubmission
    serializer_class = CollectionSubmissionSerializer
    view_category = 'collected-metadata'
    view_name = 'provider-collected-registration-metadata-list'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CollectionSubmissionCreateSerializer
        else:
            return CollectionSubmissionSerializer

    def get_default_queryset(self):
        provider = self.get_provider()
        if provider and provider.primary_collection:
            return provider.primary_collection.collectionsubmission_set.all()
        return CollectionSubmission.objects.none()

    def get_queryset(self):
        return self.get_queryset_from_request()

    def perform_create(self, serializer):
        user = self.request.user
        provider = get_object_or_error(RegistrationProvider, self.kwargs['provider_id'], self.request, display_name='RegistrationProvider')
        if provider and provider.primary_collection:
            return serializer.save(creator=user, collection=provider.primary_collection)
        raise ValidationError('Provider {} has no primary collection to submit to.'.format(provider.name))


class PreprintProviderWithdrawRequestList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, ProviderMixin):
    provider_class = PreprintProvider
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        MustBeModerator,
    )
    view_category = 'requests'
    view_name = 'provider-withdrawal-request-list'

    required_read_scopes = [CoreScopes.PREPRINT_REQUESTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = PreprintRequestSerializer

    def get_default_queryset(self):
        return PreprintRequest.objects.filter(
            request_type=RequestTypes.WITHDRAWAL.value,
            target__provider_id=self.get_provider().id,
            target__is_public=True,
            target__deleted__isnull=True,
        )

    def get_renderer_context(self):
        context = super(PreprintProviderWithdrawRequestList, self).get_renderer_context()
        if is_truthy(self.request.query_params.get('meta[requests_state_counts]', False)):
            auth = get_user_auth(self.request)
            auth_user = getattr(auth, 'user', None)
            provider = self.get_provider()
            if auth_user and auth_user.has_perm('view_submissions', provider):
                context['meta'] = {
                    'requests_state_counts': provider.get_request_state_counts(),
                }
        return context

    def get_queryset(self):
        return self.get_queryset_from_request()

class ModeratorMixin(ProviderMixin):
    provider_class = PreprintProvider
    model_class = OSFUser

    def get_provider(self):
        return get_object_or_error(self.provider_type, self.kwargs['provider_id'], self.request, display_name='PreprintProvider')

    def get_serializer_context(self, *args, **kwargs):
        ctx = super(ModeratorMixin, self).get_serializer_context(*args, **kwargs)
        ctx.update({'provider': self.get_provider()})
        return ctx


class ProviderModeratorsList(ModeratorMixin, JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        MustBeModerator,
        CanAddModerator,
    )
    view_name = 'provider-moderator-list'

    required_read_scopes = [CoreScopes.MODERATORS_READ]
    required_write_scopes = [CoreScopes.MODERATORS_WRITE]

    def get_default_queryset(self):
        provider = self.get_provider()
        admin_group = provider.get_group(ADMIN)
        mod_group = provider.get_group('moderator')
        return (admin_group.user_set.all() | mod_group.user_set.all()).annotate(permission_group=Case(
            When(groups=admin_group, then=Value(ADMIN)),
            default=Value('moderator'),
            output_field=CharField(),
        )).order_by('fullname')

    def get_queryset(self):
        return self.get_queryset_from_request()

class ProviderModeratorsDetail(ModeratorMixin, JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        MustBeModerator,
        CanUpdateModerator,
        CanDeleteModerator,
    )
    view_name = 'provider-moderator-detail'

    required_read_scopes = [CoreScopes.MODERATORS_READ]
    required_write_scopes = [CoreScopes.MODERATORS_WRITE]

    def get_object(self):
        provider = self.get_provider()
        user = get_object_or_error(OSFUser, self.kwargs['moderator_id'], self.request, display_name='OSFUser')
        try:
            perm_group = user.groups.filter(name__contains=self.provider_type.group_format.format(self=provider, group='')).order_by('name').first().name.split('_')[-1]
        except AttributeError:
            # Group doesn't exist -- users not moderator
            raise NotFound
        setattr(user, 'permission_group', perm_group)
        return user

    def perform_destroy(self, instance):
        try:
            self.get_provider().remove_from_group(instance, instance.permission_group)
        except ValueError as e:
            raise ValidationError(str(e))


class PreprintProviderModeratorsList(ProviderModeratorsList):
    provider_type = PreprintProvider
    serializer_class = PreprintModeratorSerializer

    view_category = 'preprint-providers'


class PreprintProviderModeratorsDetail(ProviderModeratorsDetail):
    provider_type = PreprintProvider
    serializer_class = PreprintModeratorSerializer

    view_category = 'preprint-providers'


class RegistrationProviderModeratorsList(ProviderModeratorsList):
    provider_type = RegistrationProvider
    serializer_class = RegistrationModeratorSerializer

    view_category = 'registration-providers'


class RegistrationProviderModeratorsDetail(ProviderModeratorsDetail):
    provider_type = RegistrationProvider
    serializer_class = RegistrationModeratorSerializer

    view_category = 'registration-providers'


class RegistrationProviderSchemaList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, ProviderMixin):
    provider_class = RegistrationProvider
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    view_category = 'registration-providers'
    view_name = 'registration-schema-list'

    required_read_scopes = [CoreScopes.SCHEMA_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationSchemaSerializer

    def get_default_queryset(self):
        provider = self.get_provider()
        default_schema_id = provider.default_schema.id if provider.default_schema else None
        schemas = provider.schemas.get_latest_versions(request=self.request, invisible=True).filter(active=True)
        if not default_schema_id:
            return schemas
        filtered = schemas.annotate(default_schema_ordering=Case(
            When(id=default_schema_id, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )).order_by('-default_schema_ordering', 'name')
        return filtered

    def get_queryset(self):
        return self.get_queryset_from_request()


class RegistrationProviderRegistrationList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, ProviderMixin):
    provider_class = RegistrationProvider
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        MustBeModerator,
    )

    ordering = ('-created')

    serializer_class = RegistrationSerializer

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'registration-providers'
    view_name = 'registrations-list'

    def get_default_queryset(self):
        provider = self.get_provider()

        return Registration.objects.filter(
            provider=provider,
        )

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides APIView
    def get_renderer_context(self):
        context = super().get_renderer_context()
        if is_truthy(self.request.query_params.get('meta[reviews_state_counts]', False)):
            provider = self.get_provider()
            context['meta'] = {
                'reviews_state_counts': provider.get_reviewable_state_counts(),
            }
        return context


class RegistrationProviderRequestList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, ProviderMixin):
    provider_class = RegistrationProvider
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        MustBeModerator,
    )
    view_category = 'requests'
    view_name = 'registration-provider-request-list'

    required_read_scopes = [CoreScopes.REGISTRATION_REQUESTS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = RegistrationRequestSerializer

    def get_default_queryset(self):
        return NodeRequest.objects.filter(
            target__provider_id=self.get_provider().id,
            target__deleted__isnull=True,
        )

    def get_queryset(self):
        return self.get_queryset_from_request()


class RegistrationProviderActionList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, ProviderMixin):
    provider_class = RegistrationProvider

    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        MustBeModerator,
    )
    view_category = 'actions'
    view_name = 'registration-provider-action-list'

    required_read_scopes = [CoreScopes.ACTIONS_READ]
    required_write_scopes = [CoreScopes.ACTIONS_WRITE]

    serializer_class = RegistrationActionSerializer

    def get_default_queryset(self):
        return RegistrationAction.objects.filter(
            target__provider_id=self.get_provider().id,
            target__deleted__isnull=True,
        )

    def get_queryset(self):
        return self.get_queryset_from_request()
