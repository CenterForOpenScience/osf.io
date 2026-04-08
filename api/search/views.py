from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView
from api.base.pagination import SearchPagination
from api.base.parsers import SearchParser
from api.base.settings import REST_FRAMEWORK, MAX_PAGE_SIZE
from api.search.permissions import IsAuthenticatedOrReadOnlyForSearch
from api.users.serializers import UserSerializer
from api.institutions.serializers import InstitutionSerializer
from api.collections.serializers import CollectionSubmissionSerializer

from framework.auth.oauth_scopes import CoreScopes
from osf.models import Institution, OSFUser, CollectionSubmission

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


class SearchUsers(BaseSearchView):
    """
    *Read-Only*

    Users that have been found by the given Elasticsearch query.

    <!-- Copied spiel from UserDetail -->

    The User Detail endpoint retrieves information about the user whose id is the final part of the path.  If `me`
    is given as the id, the record of the currently logged-in user will be returned.  The returned information includes
    the user's bibliographic information and the date that the user registered.

    Note that if an anonymous view_only key is being used, user information will not be serialized, and the id will be
    an empty string. Relationships to a user object will not show in this case, either.

    <!-- Copied attributes from UserDetail -->

    ##Attributes

    OSF User entities have the "users" `type`.

        name               type               description
        ========================================================================================
        full_name          string             full name of the user; used for display
        given_name         string             given name of the user; for bibliographic citations
        middle_names       string             middle name of user; for bibliographic citations
        family_name        string             family name of user; for bibliographic citations
        suffix             string             suffix of user's name for bibliographic citations
        date_registered    iso8601 timestamp  timestamp when the user's account was created

    <!-- Copied relationships from UserDetail -->

    ##Relationships

    ###Nodes

    A list of all nodes the user has contributed to.  If the user id in the path is the same as the logged-in user, all
    nodes will be visible.  Otherwise, you will only be able to see the other user's publicly-visible nodes.

    ##Links

        self:               the canonical api endpoint of this user
        html:               this user's page on the OSF website
        profile_image_url:  a url to the user's profile image

    ## Query Params

    + `q=<Str>` -- Query to search users for, searches across a users's given name, middle names, family name,
    first listed job, and first listed school.

    + `page=<Int>` -- page number of results to view, default 1

    # This Request/Response

    """

    model_class = OSFUser
    serializer_class = UserSerializer

    doc_type = 'user'
    view_category = 'search'
    view_name = 'search-user'


class SearchInstitutions(BaseSearchView):
    """
    *Read-Only*

    Institutions that have been found by the given Elasticsearch query.

    <!-- Copied spiel from InstitutionDetail -->

    ##Attributes

    OSF Institutions have the "institutions" `type`.

        name           type               description
        =========================================================================
        name           string             title of the institution
        id             string             unique identifier in the OSF
        logo_path      string             a path to the institution's static logo

    ##Relationships

    ###Nodes
    List of nodes that have this institution as its primary institution.

    ###Users
    List of users that are affiliated with this institution.

    ##Links

        self:  the canonical api endpoint of this institution
        html:  this institution's page on the OSF website

    # This Request/Response

    """

    model_class = Institution
    serializer_class = InstitutionSerializer

    doc_type = 'institution'
    view_category = 'search'
    view_name = 'search-institution'


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
