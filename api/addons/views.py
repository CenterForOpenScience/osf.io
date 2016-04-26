
from rest_framework.exceptions import NotFound

from api.base.settings import ADDONS_OAUTH


class AddonSettingsMixin(object):
    """Mixin with convenience methods for retrieving the current addon settings based on the
    current URL. By default, fetches the settings based on the user or node available in self context.
    """

    def get_addon_settings(self, provider=None, fail_if_absent=True):
        owner = None
        if hasattr(self, 'get_user'):
            owner = self.get_user()
        elif hasattr(self, 'get_node'):
            owner = self.get_node()

        provider = provider or self.kwargs['provider']
        if not owner or provider not in ADDONS_OAUTH:
            raise NotFound('Requested addon unavailable')

        addon_settings = owner.get_addon(provider)
        if not addon_settings and fail_if_absent:
            raise NotFound('Requested addon not enabled')

        if not addon_settings or addon_settings.deleted:
            return None

        return addon_settings
