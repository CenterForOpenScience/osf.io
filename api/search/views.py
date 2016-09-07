# -*- coding: utf-8 -*-

from rest_framework import generics, permissions as drf_permissions

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.pagination import SearchPagination
from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.search.serializers import (
    SearchSerializer,
)
from api.users.serializers import UserSerializer

from framework.auth.core import User
from framework.auth.oauth_scopes import CoreScopes, ComposedScopes

from website.files.models import FileNode
from website.models import Node
from website.search import search
from website.search.util import build_query


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

    model_class = Node
    serializer_class = NodeSerializer
    pagination_class = SearchPagination

    view_category = 'search'
    view_name = 'search-components'

    # TODO: DRY
    def get_queryset(self):
        query = self.request.query_params.get('q', '*')
        page = int(self.request.query_params.get('page', '1'))
        start = (page - 1) * 10
        return search.search(build_query(query, start=start), doc_type='component', raw=True)


class SearchFiles(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]

    model_class = FileNode
    serializer_class = FileSerializer
    pagination_class = SearchPagination

    view_category = 'search'
    view_name = 'search-files'

    # TODO: DRY
    def get_queryset(self):
        query = self.request.query_params.get('q', '*')
        page = int(self.request.query_params.get('page', '1'))
        start = (page - 1) * 10
        return search.search(build_query(query, start=start), doc_type='file', raw=True)


class SearchProjects(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]

    model_class = Node
    serializer_class = NodeSerializer
    pagination_class = SearchPagination

    view_category = 'search'
    view_name = 'search-projects'

    # TODO: DRY
    def get_queryset(self):
        query = self.request.query_params.get('q', '*')
        page = int(self.request.query_params.get('page', '1'))
        start = (page - 1) * 10
        return search.search(build_query(query, start=start), doc_type='project', raw=True)


class SearchRegistrations(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]

    model_class = Node
    pagination_class = SearchPagination
    serializer_class = RegistrationSerializer

    view_category = 'search'
    view_name = 'search-registrations'

    # TODO: DRY
    def get_queryset(self):
        query = self.request.query_params.get('q', '*')
        page = int(self.request.query_params.get('page', '1'))
        start = (page - 1) * 10
        return search.search(build_query(query, start=start), doc_type='registration', raw=True)


class SearchUsers(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]

    model_class = User
    serializer_class = UserSerializer
    pagination_class = SearchPagination

    view_category = 'search'
    view_name = 'search-users'

    # TODO: DRY
    def get_queryset(self):
        query = self.request.query_params.get('q', '*')
        page = int(self.request.query_params.get('page', '1'))
        start = (page - 1) * 10
        return search.search(build_query(query, start=start), doc_type='user', raw=True)
