from rest_framework import generics, permissions as drf_permissions

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView

from api.files.serializers import FileSerializer
from api.institutions.serializers import InstitutionSerializer
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.search.serializers import SearchSerializer
from api.users.serializers import UserSerializer

from framework.auth.oauth_scopes import CoreScopes, ComposedScopes


class Search(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [ComposedScopes.FULL_READ]

    serializer_class = SearchSerializer
    view_category = 'search'
    view_name = 'search-projects'

    def get_queryset(self):
        pass

    def get_serializer_class(self):
        pass


class SearchComponents(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]

    serializer_class = NodeSerializer
    view_category = 'search'
    view_name = 'search-components'

    def get_queryset(self):
        pass


class SearchFiles(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]

    serializer_class = FileSerializer
    view_category = 'search'
    view_name = 'search-files'

    def get_queryset(self):
        pass


class SearchInstitutions(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.INSTITUTION_READ]

    serializer_class = InstitutionSerializer
    view_category = 'search'
    view_name = 'search-institutions'

    def get_queryset(self):
        pass


class SearchProjects(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]

    serializer_class = NodeSerializer
    view_category = 'search'
    view_name = 'search-projects'

    def get_queryset(self):
        pass


class SearchRegistrations(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]

    serializer_class = RegistrationSerializer
    view_category = 'search'
    view_name = 'search-registrations'

    def get_queryset(self):
        pass


class SearchUsers(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]

    serializer_class = UserSerializer
    view_category = 'search'
    view_name = 'search-users'

    def get_queryset(self):
        pass
