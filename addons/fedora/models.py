# -*- coding: utf-8 -*-
import logging

from django.db import models
from furl import furl
from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from addons.fedora.serializer import FedoraSerializer
from addons.fedora.settings import DEFAULT_HOSTS, USE_SSL
from framework.auth import Auth
from osf.models.files import File, Folder, BaseFileNode
from osf.models.external import BasicAuthProviderMixin

logger = logging.getLogger(__name__)


class FedoraFileNode(BaseFileNode):
    _provider = 'fedora'


class FedoraFolder(FedoraFileNode, Folder):
    pass


class FedoraFile(FedoraFileNode, File):
    pass

class FedoraProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'Fedora'
    short_name = 'fedora'

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )

class UserSettings(BaseOAuthUserSettings):
    oauth_provider = FedoraProvider
    serializer = FedoraSerializer

    def to_json(self, user):
        ret = super(UserSettings, self).to_json(user)
        ret['hosts'] = DEFAULT_HOSTS
        return ret

class NodeSettings(BaseStorageAddon, BaseOAuthNodeSettings):
    oauth_provider = FedoraProvider
    serializer = FedoraSerializer

    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True)

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
        self.folder_id = folder
        self.save()
        self.nodelogger.log(action='folder_selected', save=True)

    def fetch_folder_name(self):
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
        provider = FedoraProvider(account=self.external_account)
        path = kwargs.get('path')
        url = furl(provider.host)

        # For the moment just show the path into the Fedora repository specified
        # in the account settings. In the future this could be updated to retrieve
        # subfolders from Fedora.

        return [{
            'addon': 'fedora',
            'path': str(url.path),
            'kind': 'folder',
            'id': str(url.path),
            'name': str(url.path),
            'urls': {
                'folders': ''}
        }]
