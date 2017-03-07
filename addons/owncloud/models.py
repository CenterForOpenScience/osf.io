# -*- coding: utf-8 -*-
import logging

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from framework.auth import Auth
from osf.models.files import File, FileNode, Folder
from owncloud import Client as OwnCloudClient
from addons.base import exceptions
from addons.owncloud import settings
from addons.owncloud.serializer import OwnCloudSerializer
from addons.owncloud.settings import DEFAULT_HOSTS, USE_SSL
from website.oauth.models import BasicAuthProviderMixin
from website.util import api_v2_url

logger = logging.getLogger(__name__)

class OwncloudFileNode(FileNode):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.files.models.owncloud.OwncloudFileNode'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    provider = 'owncloud'

class OwncloudFolder(OwncloudFileNode, Folder):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.files.models.owncloud.OwncloudFolder'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    pass

class OwncloudFile(OwncloudFileNode, File):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.files.models.owncloud.OwncloudFile'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    pass

class OwnCloudProvider(BasicAuthProviderMixin):
    """An alternative to `ExternalProvider` not tied to OAuth"""

    name = 'ownCloud'
    short_name = 'owncloud'

    def __init__(self, account=None, host=None, username=None, password=None):
        if username:
            username = username.lower()
        return super(OwnCloudProvider, self).__init__(account=account, host=host, username=username, password=password)

    def __repr__(self):
        return '<{name}: {status}>'.format(
            name=self.__class__.__name__,
            status=self.account.display_name if self.account else 'anonymous'
        )

class UserSettings(BaseOAuthUserSettings):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.addons.owncloud.model.AddonOwnCloudUserSettings'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    oauth_provider = OwnCloudProvider
    serializer = OwnCloudSerializer

    def to_json(self, user):
        ret = super(UserSettings, self).to_json(user)
        ret['hosts'] = DEFAULT_HOSTS
        return ret

class NodeSettings(BaseStorageAddon, BaseOAuthNodeSettings):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.addons.owncloud.model.AddonOwnCloudNodeSettings'
    modm_query = None
    # /TODO DELETE ME POST MIGRATION
    oauth_provider = OwnCloudProvider
    serializer = OwnCloudSerializer

    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True)

    _api = None

    @property
    def api(self):
        if self._api is None:
            self._api = OwnCloudProvider(self.external_account)
        return self._api

    @property
    def folder_path(self):
        return self.folder_id

    @property
    def folder_name(self):
        return self.folder_id

    def set_folder(self, folder, auth=None):
        if folder == '/ (Full ownCloud)':
            folder = '/'
        self.folder_id = folder
        self.save()
        self.nodelogger.log(action='folder_selected', save=True)

    def fetch_folder_name(self):
        if self.folder_id == '/':
            return '/ (Full ownCloud)'
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
        provider = OwnCloudProvider(self.external_account)
        return {
            'host': provider.host,
            'username': provider.username,
            'password': provider.password
        }

    def serialize_waterbutler_settings(self):
        if not self.folder_id:
            raise exceptions.AddonError('ownCloud is not configured')
        return {
            'folder': self.folder_id,
            'verify_ssl': USE_SSL
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file',
                                     path=metadata['path'], provider='owncloud')
        self.owner.add_log(
            'owncloud_{0}'.format(action),
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
        if path is None:
            return [{
                'addon': 'owncloud',
                'path': '/',
                'kind': 'folder',
                'id': '/',
                'name': '/ (Full ownCloud)',
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/owncloud/folders/'.format(self.owner._id),
                        params={
                            'path': '/',
                    })
                }
            }]

        provider = OwnCloudProvider(account=self.external_account)

        c = OwnCloudClient(provider.host, verify_certs=settings.USE_SSL)
        c.login(provider.username, provider.password)

        ret = []
        for item in c.list(path):
            if item.file_type is 'dir':
                ret.append({
                    'addon': 'owncloud',
                    'path': item.path,
                    'kind': 'folder',
                    'id': item.path,
                    'name': item.path.strip('/').split('/')[-1],
                    'urls': {
                        'folders': api_v2_url('nodes/{}/addons/owncloud/folders/'.format(self.owner._id),
                            params={
                                'path': item.path,
                        })

                    }
                })

        return ret
