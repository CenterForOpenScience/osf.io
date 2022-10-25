from rest_framework import generics, permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView

# from .serializers import MetadataProfileSerializer


class MetadataProfileList(JSONAPIBaseView, generics.ListAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.GUIDS_READ]
    required_write_scopes = [CoreScopes.NULL]

    # serializer_class = MetadataProfileSerializer
    view_category = 'metadata-profiles'
    view_name = 'metadata-profile-list'

    def get_queryset(self):
        raise NotImplementedError


class MetadataProfileDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.GUIDS_READ]
    required_write_scopes = [CoreScopes.NULL]

    # serializer_class = MetadataProfileSerializer
    view_category = 'metadata-profiles'
    view_name = 'metadata-profile-detail'

    def get_object(self):
        raise NotImplementedError
