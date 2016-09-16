# -*- coding: utf-8 -*-

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import ValidationError

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.pagination import SearchPagination
from api.base.settings import REST_FRAMEWORK, MAX_PAGE_SIZE
from api.files.serializers import FileSerializer
from api.nodes.serializers import NodeSerializer
from api.registrations.serializers import RegistrationSerializer
from api.search.serializers import SearchSerializer
from api.users.serializers import UserSerializer

from framework.auth.core import User
from framework.auth.oauth_scopes import CoreScopes

from website.files.models import FileNode
from website.models import Node
from website.search import search
from website.search.exceptions import MalformedQueryError
from website.search.util import build_query


class BaseSearchView(JSONAPIBaseView, generics.ListAPIView):

    required_read_scopes = [CoreScopes.SEARCH]
    required_write_scopes = [CoreScopes.NULL]

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
        page_size = min(int(self.request.query_params.get('page[size]', REST_FRAMEWORK['PAGE_SIZE'])), MAX_PAGE_SIZE)
        start = (page - 1) * page_size
        try:
            results = search.search(build_query(query, start=start, size=page_size), doc_type=self.doc_type, raw=True)
        except MalformedQueryError as e:
            raise ValidationError(e.message)
        return results


class Search(BaseSearchView):

    serializer_class = SearchSerializer

    view_category = 'search'
    view_name = 'search-search'


class SearchComponents(BaseSearchView):

    model_class = Node
    serializer_class = NodeSerializer

    doc_type = 'component'
    view_category = 'search'
    view_name = 'search-component'


class SearchFiles(BaseSearchView):

    model_class = FileNode
    serializer_class = FileSerializer

    doc_type = 'file'
    view_category = 'search'
    view_name = 'search-file'


class SearchProjects(BaseSearchView):

    model_class = Node
    serializer_class = NodeSerializer

    doc_type = 'project'
    view_category = 'search'
    view_name = 'search-project'


class SearchRegistrations(BaseSearchView):

    model_class = Node
    serializer_class = RegistrationSerializer

    doc_type = 'registration'
    view_category = 'search'
    view_name = 'search-registration'


class SearchUsers(BaseSearchView):

    model_class = User
    serializer_class = UserSerializer

    doc_type = 'user'
    view_category = 'search'
    view_name = 'search-user'
