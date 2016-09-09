# -*- coding: utf-8 -*-

from rest_framework import generics, permissions as drf_permissions

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.pagination import SearchPagination
from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.search.serializers import SearchSerializer
from api.users.serializers import UserSerializer

from framework.auth.core import User
from framework.auth.oauth_scopes import CoreScopes, ComposedScopes

from website.files.models import FileNode
from website.models import Node
from website.search import search
from website.search.util import build_query


class BaseSearchView(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    pagination_class = SearchPagination

    def __init__(self):
        super(BaseSearchView, self).__init__()
        self.doc_type = getattr(self, 'doc_type', None)

    def get_queryset(self):
        query = self.request.query_params.get('q', '*')
        page = int(self.request.query_params.get('page', '1'))
        start = (page - 1) * 10
        return search.search(build_query(query, start=start), doc_type=self.doc_type, raw=True)


class Search(BaseSearchView):

    required_read_scopes = [ComposedScopes.FULL_READ]

    serializer_class = SearchSerializer

    view_category = 'search'
    view_name = 'search-search'


class SearchComponents(BaseSearchView):

    required_read_scopes = [CoreScopes.NODE_BASE_READ]

    model_class = Node
    serializer_class = NodeSerializer

    doc_type = 'component'
    view_category = 'search'
    view_name = 'search-component'


class SearchFiles(BaseSearchView):

    required_read_scopes = [CoreScopes.NODE_FILE_READ]

    model_class = FileNode
    serializer_class = FileSerializer

    doc_type = 'file'
    view_category = 'search'
    view_name = 'search-file'


class SearchProjects(BaseSearchView):

    required_read_scopes = [CoreScopes.NODE_BASE_READ]

    model_class = Node
    serializer_class = NodeSerializer

    doc_type = 'project'
    view_category = 'search'
    view_name = 'search-project'


class SearchRegistrations(BaseSearchView):

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]

    model_class = Node
    serializer_class = RegistrationSerializer

    doc_type = 'registration'
    view_category = 'search'
    view_name = 'search-registration'


class SearchUsers(BaseSearchView):

    required_read_scopes = [CoreScopes.USERS_READ]

    model_class = User
    serializer_class = UserSerializer

    doc_type = 'user'
    view_category = 'search'
    view_name = 'search-user'
