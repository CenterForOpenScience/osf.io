from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from framework.auth.oauth_scopes import CoreScopes, public_scopes

from api.base.filters import ListFilterMixin
from api.base import permissions as base_permissions
from api.scopes.serializers import ScopeSerializer, Scope
from api.scopes.permissions import IsPublicScope
from api.base.views import JSONAPIBaseView
from api.base.pagination import MaxSizePagination


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
        scope_item = public_scopes.get(id, None)
        if scope_item:
            scope = Scope(id=id, scope=scope_item)
            self.check_object_permissions(self.request, scope)
            return scope
        else:
            raise NotFound


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
        scopes = []
        for key, value in public_scopes.items():
            if value.is_public:
                scopes.append(Scope(id=key, scope=value))
        return scopes

    def get_queryset(self):
        return self.get_queryset_from_request()
