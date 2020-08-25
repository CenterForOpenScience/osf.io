from rest_framework import permissions as drf_permissions, exceptions

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.pagination import DraftRegistrationContributorPagination
from api.draft_registrations.permissions import (
    DraftContributorDetailPermissions,
    IsContributorOrAdminContributor,
    IsAdminContributor,
)
from api.draft_registrations.serializers import (
    DraftRegistrationSerializer,
    DraftRegistrationDetailSerializer,
    DraftRegistrationContributorsSerializer,
    DraftRegistrationContributorDetailSerializer,
    DraftRegistrationContributorsCreateSerializer,
)
from api.nodes.views import (
    NodeDraftRegistrationsList,
    NodeDraftRegistrationDetail,
    NodeInstitutionsList,
    NodeInstitutionsRelationship,
    NodeContributorsList,
    NodeContributorDetail,
    DraftMixin,
)
from api.nodes.permissions import ContributorOrPublic, AdminDeletePermissions
from api.subjects.views import SubjectRelationshipBaseView, BaseResourceSubjectsList
from osf.models import DraftRegistrationContributor

class DraftRegistrationMixin(DraftMixin):
    """
    Old DraftMixin was built under the assumption that a node was provided from the start.
    All permission checking went through the node, not the draft.
    New draft registration endpoints do permission checking on the draft registration.
    """

    # Overrides DraftMixin
    def check_branched_from(self, draft):
        # We do not have to check the branched_from relationship. node_id is not a kwarg
        return

    # Overrides DraftMixin
    def check_resource_permissions(self, resource):
        # Checks permissions on draft_registration, regardless of whether or not
        # draft_registration is branched off of a node
        return self.check_object_permissions(self.request, resource)


class DraftRegistrationList(NodeDraftRegistrationsList):
    permission_classes = (
        IsContributorOrAdminContributor,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_registrations'
    view_name = 'draft-registration-list'

    # overrides NodeDraftRegistrationList
    def get_serializer_class(self):
        return DraftRegistrationSerializer

    # overrides NodeDraftRegistrationList
    def get_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            raise exceptions.NotAuthenticated()
        # Returns DraftRegistrations for which a user is a contributor
        return user.draft_registrations_active


class DraftRegistrationDetail(NodeDraftRegistrationDetail, DraftRegistrationMixin):
    permission_classes = (
        IsContributorOrAdminContributor,
        AdminDeletePermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_registrations'
    view_name = 'draft-registration-detail'

    # overrides NodeDraftRegistrationDetail
    def get_serializer_class(self):
        return DraftRegistrationDetailSerializer


class DraftInstitutionsList(NodeInstitutionsList, DraftRegistrationMixin):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ, CoreScopes.DRAFT_REGISTRATIONS_READ]

    view_category = 'draft_registrations'
    view_name = 'draft-registration-institutions'

    # Overrides NodeInstitutionsList
    def get_resource(self):
        return self.get_draft()


class DraftInstitutionsRelationship(NodeInstitutionsRelationship, DraftRegistrationMixin):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_registrations'
    view_name = 'draft-registration-relationships-institutions'

    # Overrides NodeInstitutionsRelationship
    def get_resource(self):
        return self.get_draft(check_object_permissions=False)


class DraftSubjectsList(BaseResourceSubjectsList, DraftRegistrationMixin):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.DRAFT_REGISTRATIONS_READ]

    view_category = 'draft_registrations'
    view_name = 'draft-registration-subjects'

    def get_resource(self):
        # Overrides BaseResourceSubjectsList
        return self.get_draft()


class DraftSubjectsRelationship(SubjectRelationshipBaseView, DraftRegistrationMixin):
    permission_classes = (
        ContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.DRAFT_REGISTRATIONS_WRITE]

    view_category = 'draft_registrations'
    view_name = 'draft-registration-relationships-subjects'

    ordering = ('-id',)

    def get_resource(self, check_object_permissions=True):
        # Overrides SubjectRelationshipBaseView
        return self.get_draft(check_object_permissions=check_object_permissions)


class DraftContributorsList(NodeContributorsList, DraftRegistrationMixin):
    permission_classes = (
        IsAdminContributor,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    pagination_class = DraftRegistrationContributorPagination

    required_read_scopes = [CoreScopes.DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.DRAFT_REGISTRATIONS_WRITE]

    view_category = 'draft_registrations'
    view_name = 'draft-registration-contributors'
    serializer_class = DraftRegistrationContributorsSerializer

    def get_default_queryset(self):
        # Overrides NodeContributorsList
        draft = self.get_draft()
        return draft.draftregistrationcontributor_set.all().include('user__guids')

    # overrides NodeContributorsList
    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return DraftRegistrationContributorDetailSerializer
        elif self.request.method == 'POST':
            return DraftRegistrationContributorsCreateSerializer
        else:
            return DraftRegistrationContributorsSerializer

    def get_resource(self):
        return self.get_draft()

    # Overrides NodeContributorsList
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['resource'] = self.get_resource()
        context['default_email'] = 'draft_registration'
        return context


class DraftContributorDetail(NodeContributorDetail, DraftRegistrationMixin):
    permission_classes = (
        DraftContributorDetailPermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    view_category = 'draft_registrations'
    view_name = 'draft-registration-contributor-detail'
    serializer_class = DraftRegistrationContributorDetailSerializer

    required_read_scopes = [CoreScopes.DRAFT_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.DRAFT_CONTRIBUTORS_WRITE]

    def get_resource(self):
        return self.get_draft()

    # overrides RetrieveAPIView
    def get_object(self):
        draft_registration = self.get_draft()
        user = self.get_user()
        # May raise a permission denied
        self.check_object_permissions(self.request, user)
        try:
            return draft_registration.draftregistrationcontributor_set.get(user=user)
        except DraftRegistrationContributor.DoesNotExist:
            raise exceptions.NotFound('{} cannot be found in the list of contributors.'.format(user))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['resource'] = self.get_draft()
        context['default_email'] = 'draft'
        return context
