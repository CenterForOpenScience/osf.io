from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound, PermissionDenied

from framework.auth import Auth
from framework.auth.oauth_scopes import CoreScopes

from website.addons.base import AddonOAuthUserSettingsBase, AddonNodeSettingsBase
from website import settings as website_settings

from api.base import permissions as base_permissions
from api.external_accounts.serializers import ExternalAccountSerializer
from api.user_addons.serializers import (
    UserAddonSerializer,
    UserAddonLinkedNodeSerializer,
    UserAddonLinkedNodeCreateSerializer
)


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


class UserAddonNodeAddonList(generics.ListCreateAPIView, ExternalAccountMixin):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.NODE_ADDONS_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE, CoreScopes.NODE_ADDONS_WRITE]

    lookup_field = 'external_account_id'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserAddonLinkedNodeCreateSerializer
        else:
            return UserAddonLinkedNodeSerializer

    # overrides ListAPIView
    def get_queryset(self):
        user_addon = self.get_user_addon()
        provider = user_addon.config.short_name
        return [
            node.get_addon(provider)
            for node in user_addon.nodes_authorized
        ]


class UserAddonNodeAddonDetail(generics.RetrieveDestroyAPIView, UserAddonMixin):

    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.NODE_ADDONS_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE, CoreScopes.NODE_ADDONS_WRITE]

    serializer_class = UserAddonLinkedNodeSerializer

    lookup_field = 'node_addon_id'

    def _get_node_addon_model(self, provider):
        models = website_settings.ADDONS_AVAILABLE_DICT[provider].models
        model = None
        for model in models:
            if isinstance(model, AddonNodeSettingsBase):
                break
        return model

    def _get_node_addon(self):
        node_addon_id = self.kwargs[self.lookup_field]
        user_addon = self.get_user_addon()
        provider = user_addon.config.short_name
        node_addon_model = self._get_node_addon_model(provider)
        node_addon = node_addon_model.load(node_addon_id)
        return node_addon

    def get_object(self):
        return self._get_node_addon()

    def permform_destroy(self, node):
        current_user = self.request.user
        user_addon = self.get_user_addon()
        node_addon = node.get_addon(user_addon.config.short_name)
        if node_addon:
            node_addon.deauthorize(auth=Auth(current_user))
