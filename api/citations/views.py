from rest_framework import generics, permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.base.utils import get_object_or_error
from api.base.filters import ODMFilterMixin
from api.base.pagination import NoMaxPageSizePagination
from api.base import permissions as base_permissions
from api.citations.serializers import CitationSerializer
from website.project.taxonomies import Subject
from framework.auth.oauth_scopes import CoreScopes

from website.models import CitationStyle

class CitationList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    '''List of citations for a specific node. *Read-only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

    ##Citation Attributes

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

class CitationDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    '''Detail for a citation for a specific node*Read-only*

    ##Note
    **This API endpoint is under active development, and is subject to change in the future**

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
        return get_object_or_error(CitationStyle, self.kwargs['citation_id'])
