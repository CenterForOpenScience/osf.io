from rest_framework import generics, permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.filters import ODMFilterMixin
from api.base.pagination import NoMaxPageSizePagination
from api.base import permissions as base_permissions
from api.citations.serializers import CitationSerializer
from framework.auth.oauth_scopes import CoreScopes

from website.models import CitationStyle

class CitationStyleList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    '''List of standard citation styles available for rendering citations. *Read-only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##Citation Attributes

            name           type               description
        =========================================================================
        date_parsed        string             date the citation style was first added to the database
        summary            string             summary of the citation style
        short_title        string             a short name or nickname for the citation style
        title              string             official name of the citation style


    Citation style may be filtered by their 'title', 'short_title', 'summary', and 'id'
    '''
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = CitationSerializer
    pagination_class = NoMaxPageSizePagination
    view_category = 'citations'
    view_name = 'citation-list'

    # overrides ListAPIView
    def get_default_odm_query(self):
        return

    def get_queryset(self):
        return CitationStyle.find(self.get_query_from_request())

class CitationStyleDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    '''Detail for a citation style *Read-only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##Citation Attributes

        name           type               description
    =========================================================================
    date_parsed        string             date the citation style was first added to the database
    summary            string             summary of the citation style
    short_title        string             a short name or nickname for the citation style
    title              string             official name of the citation style

    '''
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope
    )

    required_read_scopes = [CoreScopes.ALWAYS_PUBLIC]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = CitationSerializer
    view_category = 'citations'
    view_name = 'citation-detail'

    def get_object(self):
        cit = get_object_or_error(CitationStyle, self.kwargs['citation_id'])
        self.check_object_permissions(self.request, cit)
        return cit
