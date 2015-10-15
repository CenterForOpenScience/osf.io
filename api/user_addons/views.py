from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound, PermissionDenied

from framework.auth import Auth
from framework.auth.oauth_scopes import CoreScopes

from api.base.utils import get_object_or_error
from api.base import permissions as base_permissions
from api.external_accounts.serializers import ExternalAccountSerializer
from api.user_addons.serializers import UserAddonSerializer, UserAddonNodeSerializer

from website.models import Node
from website.addons.base import AddonOAuthUserSettingsBase


class UserAddonMixin(object):

    def get_user_addon(self):
        current_user = self.request.user
        user_addons = current_user.get_addons()

        user_addon_id = self.kwargs['user_addon_id']
        for addon in user_addons:
            if user_addon_id == addon.pk:
                return addon
        raise NotFound()


class ExternalAccountMixin(UserAddonMixin):

    def get_external_account(self, kwargs=None):
        kwargs = kwargs or self.kwargs
        user_addon = self.get_user_addon()
        external_accounts = []
        if isinstance(user_addon, AddonOAuthUserSettingsBase):
            external_accounts = user_addon.external_accounts
        else:
            external_accounts = [user_addon]

        external_account_id = kwargs[self.lookup_field]
        for account in external_accounts:
            if external_account_id == account.pk:
                return account


class UserAddonDetail(generics.RetrieveAPIView, UserAddonMixin):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USER_ADDONS_READ]
    required_write_scopes = [CoreScopes.USER_ADDONS_WRITE]

    serializer_class = UserAddonSerializer

    lookup_field = 'user_addon_id'

    def get_object(self):
        return self.get_user_addon()

class UserAddonAccountList(generics.ListAPIView, UserAddonMixin):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.EXTERNAL_ACCOUNTS_READ]
    required_write_scopes = [CoreScopes.EXTERNAL_ACCOUNTS_WRITE]

    serializer_class = ExternalAccountSerializer

    # overrides ListAPIView
    def get_queryset(self):
        user_addon = self.get_user_addon()
        if isinstance(user_addon, AddonOAuthUserSettingsBase):
            return user_addon.extnernal_accounts
        else:
            return [user_addon]


class UserAddonAccountDetail(generics.RetrieveDestroyAPIView, ExternalAccountMixin):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.EXTERNAL_ACCOUNTS_READ]
    required_write_scopes = [CoreScopes.EXTERNAL_ACCOUNTS_WRITE]

    serializer_class = ExternalAccountSerializer

    lookup_field = 'external_account_id'

    def get_object(self):
        return self.get_external_account()

    def perform_destroy(self, instance):
        current_user = self.request.user
        user_addon = self.get_user_addon()
        external_account = self.get_external_account()
        if external_account:
            provider = external_account.provider
            target_user_addon = current_user.get_addon(provider)
            if not user_addon.pk == target_user_addon.pk:
                raise PermissionDenied()
            else:
                user_addon.remove_account(external_account, auth=Auth(current_user), save=True)
        else:
            raise NotFound()


class UserAddonNodeList(generics.ListCreateAPIView, ExternalAccountMixin):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    serializer_class = UserAddonNodeSerializer

    lookup_field = 'external_account_id'

    # overrides ListAPIView
    def get_queryset(self):
        user_addon = self.get_user_addon()
        return user_addon.nodes_authorized


class UserAddonNodeDetail(generics.RetrieveDestroyAPIView, UserAddonMixin):

    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.USER_ADDONS_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE, CoreScopes.USER_ADDONS_WRITE]

    serializer_class = UserAddonNodeSerializer

    lookup_field = 'node_id'

    def _get_node(self):
        node_id = self.kwargs[self.lookup_field]
        user_addon = self.get_user_addon()
        nodes_authorized = user_addon.nodes_authorized
        for node in nodes_authorized:
            if node_id == node.pk:
                return node
        raise NotFound()

    def get_object(self):
        return self._get_node()

    def permform_destroy(self, node):
        current_user = self.request.user
        user_addon = self.get_user_addon()
        node_addon = node.get_addon(user_addon.config.short_name)
        if node_addon:
            node_addon.deauthorize(auth=Auth(current_user))
