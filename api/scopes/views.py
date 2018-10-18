from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from framework.auth.oauth_scopes import CoreScopes

from api.base.filters import ListFilterMixin
from api.base import permissions as base_permissions
from api.scopes.serializers import ScopeSerializer
from api.scopes.permissions import IsPublicScope
from api.base.views import JSONAPIBaseView
from api.base.pagination import MaxSizePagination
from osf.models.oauth import ApiOAuth2Scope


class ScopeDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    """Private endpoint for gathering scope information. Do not expect this to be stable.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsPublicScope,
    )

    required_read_scopes = [CoreScopes.SCOPES_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = ScopeSerializer
    view_category = 'scopes'
    view_name = 'scope-detail'
    lookup_url_kwarg = 'scope_id'

    # overrides RetrieveAPIView
    def get_object(self):
        id = self.kwargs[self.lookup_url_kwarg]
        try:
            scope = ApiOAuth2Scope.objects.get(name=id)
        except ApiOAuth2Scope.DoesNotExist:
            raise NotFound

        self.check_object_permissions(self.request, scope)
        return scope


class ScopeList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    """Private endpoint for gathering scope information. Do not expect this to be stable.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsPublicScope,
    )

    required_read_scopes = [CoreScopes.SCOPES_READ]
    required_write_scopes = [CoreScopes.NULL]

    pagination_class = MaxSizePagination
    serializer_class = ScopeSerializer
    view_category = 'scopes'
    view_name = 'scope-list'

    ordering = ('id', )  # default ordering

    def get_default_queryset(self):
        return ApiOAuth2Scope.objects.filter(is_public=True)

    def get_queryset(self):
        return self.get_queryset_from_request()
