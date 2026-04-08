from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.pagination import SearchPagination
from api.base.parsers import SearchParser
from api.base.settings import REST_FRAMEWORK, MAX_PAGE_SIZE
from api.search.permissions import IsAuthenticatedOrReadOnlyForSearch
from api.collections.serializers import CollectionSubmissionSerializer

from framework.auth.oauth_scopes import CoreScopes
from osf.models import CollectionSubmission

from website.search import search
from website.search.exceptions import MalformedQueryError
from website.search.util import build_query
from api.base.filters import ElasticOSFOrderingFilter


class BaseSearchView(JSONAPIBaseView, generics.ListCreateAPIView):

    required_read_scopes = [CoreScopes.SEARCH]
    required_write_scopes = [CoreScopes.NULL]

    permission_classes = (
        IsAuthenticatedOrReadOnlyForSearch,
        base_permissions.TokenHasScope,
    )

    pagination_class = SearchPagination
    filter_backends = [ElasticOSFOrderingFilter]

    @property
    def search_fields(self):
        # Should be overridden in subclasses to provide a list of keys found
        # in the relevant elastic doc.
        raise NotImplementedError

    def __init__(self):
        super().__init__()
        self.doc_type = getattr(self, 'doc_type', None)

    def get_parsers(self):
        if self.request.method == 'POST':
            return (SearchParser(),)
        return super().get_parsers()

    def get_queryset(self, query=None):
        page = int(self.request.query_params.get('page', '1'))
        page_size = min(int(self.request.query_params.get('page[size]', REST_FRAMEWORK['PAGE_SIZE'])), MAX_PAGE_SIZE)
        start = (page - 1) * page_size
        if query:
            # Parser has built query, but needs paging info
            query['from'] = start
            query['size'] = page_size
        else:
            query = build_query(self.request.query_params.get('q', '*'), start=start, size=page_size)
        try:
            results = search.search(query, doc_type=self.doc_type, raw=True)
        except MalformedQueryError as e:
            raise ValidationError(e)
        return results


class SearchCollections(BaseSearchView):
    """
    """

    model_class = CollectionSubmission
    serializer_class = CollectionSubmissionSerializer

    doc_type = 'collectionSubmission'
    view_category = 'search'
    view_name = 'search-collected-metadata'
    required_write_scopes = [CoreScopes.ADVANCED_SEARCH]

    @property
    def search_fields(self):
        return [
            'abstract',
            'collectedType',
            'contributors.fullname',
            'status',
            'subjects',
            'provider',
            'title',
            'tags',
        ]

    def create(self, request, *args, **kwargs):
        # Override POST methods to behave like list, with header query parsing
        queryset = self.filter_queryset(self.get_queryset(request.data))
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
