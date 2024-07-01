from django.db import models

from addons.base.exceptions import NotApplicableError
from addons.base.models import BaseOAuthNodeSettings, BaseOAuthUserSettings, BaseStorageAddon
from addons.boa.serializer import BoaSerializer
from addons.boa.settings import DEFAULT_HOSTS
from framework.auth import Auth
from osf.models.external import BasicAuthProviderMixin


class BoaProvider(BasicAuthProviderMixin):
    """Boa provider, an alternative to `ExternalProvider` which is not tied to OAuth"""

    name = 'Boa'
    short_name = 'boa'

    def __init__(self, account=None, host=None, username=None, password=None):
        if username:
            username = username.lower()
        super().__init__(account=account, host=host, username=username, password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )


class UserSettings(BaseOAuthUserSettings):

    oauth_provider = BoaProvider
    serializer = BoaSerializer

    def to_json(self, user):
        ret = super().to_json(user)
        ret['hosts'] = DEFAULT_HOSTS
        return ret


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):

    oauth_provider = BoaProvider
    serializer = BoaSerializer

    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    _api = None

    @property
    def api(self):
        if self._api is None:
            self._api = BoaProvider(self.external_account)
        return self._api

    @property
    def folder_path(self):
        return self.folder_id

    @property
    def folder_name(self):
        return self.folder_id

    def set_folder(self, folder, auth=None):
        """Not applicable to remote computing add-on."""
        raise NotApplicableError

    def fetch_folder_name(self):
        if self.folder_id == '/':
            return '/ (Full Boa)'
        return self.folder_id.strip('/').split('/')[-1]

    def clear_settings(self):
        self.folder_id = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        if add_log:
            self.nodelogger.log(action='node_deauthorized')
        self.clear_auth()  # Also performs a .save()

    def serialize_waterbutler_credentials(self):
        """Not applicable to remote computing add-on."""
        raise NotApplicableError

    def serialize_waterbutler_settings(self):
        """Not applicable to remote computing add-on."""
        raise NotApplicableError

    def create_waterbutler_log(self, *args, **kwargs):
        """Not applicable to remote computing add-on."""
        raise NotApplicableError

    def after_delete(self, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()

    def get_folders(self, **kwargs):
        """Not applicable to remote computing add-on."""
        raise NotApplicableError
