from rest_framework import generics
from rest_framework import permissions as drf_permissions

from framework.auth.oauth_scopes import CoreScopes

from api.base import permissions as base_permissions
from api.nodes.serializers import NodeSerializer
from api.external_accounts.serializers import ExternalAccountSerializer

from website.addons.base import AddonOAuthUserSettingsBase

class ExternalAccountMixin(object):
    serializer_class = ExternalAccountSerializer

    def get_external_account(self):
        current_user = self.request.user
        user_addons = current_user.get_addons()
        external_account_id = self.kwargs['external_account_id']
        external_account = None
        for addon in user_addons:
            if external_account:
                break
            if isinstance(addon, AddonOAuthUserSettingsBase):
                for account in addon.external_accounts:
                    if external_account_id == account.pk:
                        external_account = account
                        break
            else:
                if external_account_id == addon.pk:
                    external_account = addon
        return external_account


class ExternalAccountDetail(generics.RetrieveAPIView, ExternalAccountMixin):
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
