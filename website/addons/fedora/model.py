# -*- coding: utf-8 -*-
import logging
from modularodm import fields
from framework.auth import Auth
from website.addons.base import exceptions
from website.addons.base import StorageAddonBase
from website.addons.base import (
    AddonOAuthNodeSettingsBase, AddonOAuthUserSettingsBase,
)
from website.addons.fedora.serializer import FedoraSerializer
from website.addons.fedora.settings import DEFAULT_HOSTS, USE_SSL
from website.addons.fedora import settings

from website.oauth.models import BasicAuthProviderMixin
from website.util import api_v2_url

logger = logging.getLogger(__name__)

class FedoraProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'fedora'
    short_name = 'fedora'

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )

class AddonFedoraUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = FedoraProvider
    serializer = FedoraSerializer

    def to_json(self, user):
        ret = super(AddonFedoraUserSettings, self).to_json(user)
        ret['hosts'] = DEFAULT_HOSTS
        return ret

class AddonFedoraNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = FedoraProvider
    serializer = FedoraSerializer

    folder_id = fields.StringField()

    _api = None

    @property
    def api(self):
        if self._api is None:
            self._api = FedoraProvider(self.external_account)
        return self._api

    @property
    def folder_path(self):
        return self.folder_id

    @property
    def folder_name(self):
        return self.folder_id

    def set_folder(self, folder, auth=None):
        if folder == '/ (Full fedora)':
            folder = '/'
        self.folder_id = folder
        self.save()
        self.nodelogger.log(action='folder_selected', save=True)

    def fetch_folder_name(self):
        if self.folder_id == '/':
            return '/ (Full fedora)'
        return self.folder_id.strip('/').split('/')[-1]

    def clear_settings(self):
        self.folder_id = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        self.clear_settings()
        self.nodelogger.log(action='node_deauthorized')
        self.clear_auth()  # Also performs a .save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        provider = FedoraProvider(self.external_account)
        return {
            'repo': provider.host,
            'user': provider.username,
            'password': provider.password
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('fedora is not configured')
        return {
            'folder': self.folder_id,
            'verify_ssl': USE_SSL
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file',
                                     path=metadata['path'], provider='fedora')
        self.owner.add_log(
            'fedora_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_id,
                'path': metadata['materialized'].strip('/'),
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()

    def get_folders(self, **kwargs):
        path = kwargs.get('path')
        return [{
            'addon': 'fedora',
            'path': '/',
            'kind': 'folder',
            'id': '/',
            'name': '/ (Full fedora)',
            'urls': {
                'folders': ''}
        }]
