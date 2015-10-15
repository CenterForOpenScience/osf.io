from rest_framework import generics
from rest_framework import permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.node_addons.serializers import NodeAddonSerializer

class NodeAddonDetail(generics.RetrieveAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_ADDONS_READ]
    required_write_scopes = [CoreScopes.NODE_ADDONS_WRITE]

    serializer_class = NodeAddonSerializer

    def get_queryset(self):
        pass

    def get_object(self):
        pass
