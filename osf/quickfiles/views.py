from api.base.views import JSONAPIBaseView, WaterButlerMixin
from api.users.views import UserMixin, ListFilterMixin

from rest_framework import generics
from rest_framework import permissions as drf_permissions
from api.base import permissions as base_permissions
from framework.auth.oauth_scopes import CoreScopes
from osf.quickfiles.serializers import UserQuickFilesSerializer


class UserQuickFiles(JSONAPIBaseView, generics.ListAPIView, WaterButlerMixin, UserMixin, ListFilterMixin):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    ordering = ('-last_touched')

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = UserQuickFilesSerializer
    view_category = 'users'
    view_name = 'user-quickfiles'

    def get_resource(self, check_object_permissions):
        return self.get_user(check_permissions=False)

    def get_default_queryset(self):
        self.kwargs[self.path_lookup_url_kwarg] = '/'
        self.kwargs[self.provider_lookup_url_kwarg] = 'osfstorage'
        files_list = self.fetch_from_waterbutler()

        return files_list.children.prefetch_related('versions', 'tags').include('guids')

    # overrides ListAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()
