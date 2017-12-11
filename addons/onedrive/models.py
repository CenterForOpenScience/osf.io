# -*- coding: utf-8 -*-
import os
import urllib
import logging

from django.db import models

from addons.base import exceptions
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from addons.onedrive import settings
from addons.onedrive.client import OneDriveClient
from addons.onedrive.settings import DEFAULT_ROOT_ID
from addons.onedrive.serializer import OneDriveSerializer
from framework.auth import Auth
from framework.exceptions import HTTPError
from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from website.util import api_v2_url

logger = logging.getLogger(__name__)


class OneDriveFileNode(BaseFileNode):
    _provider = 'onedrive'


class OneDriveFolder(OneDriveFileNode, Folder):
    pass


class OneDriveFile(OneDriveFileNode, File):
    @property
    def _hashes(self):
        try:
            return {'md5': self._history[-1]['extra']['hashes']['md5']}
        except (IndexError, KeyError):
            return None


class OneDriveProvider(ExternalProvider):
    name = 'Microsoft OneDrive'
    short_name = 'onedrive'

    client_id = settings.ONEDRIVE_KEY
    client_secret = settings.ONEDRIVE_SECRET

    auth_url_base = settings.ONEDRIVE_OAUTH_AUTH_ENDPOINT
    callback_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    default_scopes = ['wl.basic wl.signin onedrive.readwrite wl.offline_access']

    refresh_time = settings.REFRESH_TIME

    _drive_client = OneDriveClient()

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new OneDriveUserSettings
        record to the user and saves the user's access token and account info.
        """
        user_info = self._drive_client.user_info_for_token(response['access_token'])

        return {
            'provider_id': user_info['id'],
            'display_name': user_info['name'],
            'profile_url': user_info['link']
        }

    def fetch_access_token(self, force_refresh=False):
        self.refresh_oauth_key(force=force_refresh)
        return self.account.oauth_key


class UserSettings(BaseOAuthUserSettings):
    """Stores user-specific onedrive information
    """
    oauth_provider = OneDriveProvider
    serializer = OneDriveSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    """Individual OneDrive settings for a particular node.

    QUIRKS::

    * OneDrive personal and OneDrive for Business users will have only one drive
      available.  This addon is built around this assumption.  Users using this with
      a SharePoint team site will have several other drives available, but this use
      case is not supported or tested.  See:
      https://dev.onedrive.com/drives/list-drives.htm#remarks

    * OneDrive is an ID-based provider like Box. The identifier for the root folder
      is defined in the settings.

    """
    oauth_provider = OneDriveProvider
    serializer = OneDriveSerializer

    folder_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = OneDriveProvider(self.external_account)
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
        ))

    @property
    def folder_name(self):
        if not self.folder_id:
            return None

        if self.folder_id != DEFAULT_ROOT_ID:
            # `urllib` does not properly handle unicode.
            # encode input to `str`, decode output back to `unicode`
            return urllib.unquote(os.path.split(self.folder_path)[1].encode('utf-8')).decode('utf-8')
        else:
            return '/ (Full OneDrive)'

    def fetch_folder_name(self):
        """Required.  Called by base views"""
        return self.folder_name

    def clear_settings(self):
        self.folder_id = None
        self.folder_path = None

    def get_folders(self, folder_id=None, **kwargs):
        """Get list of folders underneath the folder with id ``folder_id``.  If
        ``folder_id`` is ``None``, return a single entry representing the root folder.
        In OneDrive, the root folder has a unique id, so fetch that and return it.

        This method returns a list of dicts with metadata about each folder under ``folder_id``.
        These dicts have the following properties::

            {
                'addon': 'onedrive',          # short name of the addon
                'id': folder_id,              # id of the folder.  root may need special casing
                'path': '/',                  # human-readable path of the folder
                'kind': 'folder',             # always 'folder'
                'name': '/ (Full OneDrive)',  # human readable name of the folder. root may need special casing
                'urls': {                     # urls to fetch information about the folder
                    'folders': api_v2_url(    # url to get subfolders of this folder.
                        'nodes/{}/addons/onedrive/folders/'.format(self.owner._id),
                         params={'id': folder_id}
                    ),
                }
            }

        Some providers include additional information::

        * figshare includes ``permissions``, ``hasChildren``

        * googledrive includes ``urls.fetch``

        :param str folder_id: the id of the folder to fetch subfolders of. Defaults to ``None``
        :rtype: list
        :return: a list of dicts with metadata about the subfolder of ``folder_id``.
        """

        if folder_id is None:
            return [{
                'id': DEFAULT_ROOT_ID,
                'path': '/',
                'addon': 'onedrive',
                'kind': 'folder',
                'name': '/ (Full OneDrive)',
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/onedrive/folders/'.format(self.owner._id),
                                          params={'id': DEFAULT_ROOT_ID}),
                }
            }]

        try:
            access_token = self.fetch_access_token()
        except exceptions.InvalidAuthError:
            raise HTTPError(403)

        client = OneDriveClient(access_token)
        items = client.folders(folder_id)
        return [
            {
                'addon': 'onedrive',
                'kind': 'folder',
                'id': item['id'],
                'name': item['name'],
                'path': item['name'],
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/onedrive/folders/'.format(self.owner._id),
                                          params={'id': item['id']}),
                }
            }
            for item in items
        ]

    def set_folder(self, folder, auth):
        self.folder_id = folder['id']
        self.folder_path = folder['path']
        self.save()

        if not self.complete:
            self.user_settings.grant_oauth_access(
                node=self.owner,
                external_account=self.external_account,
                metadata={'folder': self.folder_id}
            )
            self.user_settings.save()

        self.nodelogger.log(action='folder_selected', save=True)

    @property
    def selected_folder_name(self):
        if self.folder_id is None:
            return ''
        elif self.folder_id == DEFAULT_ROOT_ID:
            return '/ (Full OneDrive)'
        else:
            return self.folder_name

    def deauthorize(self, auth=None, add_log=True, save=False):
        """Remove user authorization from this node and log the event."""

        if add_log:
            extra = {'folder_id': self.folder_id}
            self.nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.clear_settings()
        self.clear_auth()

        if save:
            self.save()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fetch_access_token()}

    def serialize_waterbutler_settings(self):
        if self.folder_id is None:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder_id}

    def create_waterbutler_log(self, auth, action, metadata):
        self.owner.add_log(
            'onedrive_{0}'.format(action),
            auth=auth,
            params={
                'path': metadata['path'],
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_path,
                'urls': {
                    'view': self.owner.web_url_for(
                        'addon_view_or_download_file',
                        provider='onedrive',
                        action='view',
                        path=metadata['path']
                    ),
                    'download': self.owner.web_url_for(
                        'addon_view_or_download_file',
                        provider='onedrive',
                        action='download',
                        path=metadata['path']
                    ),
                },
            },
        )

    def fetch_access_token(self):
        return self.api.fetch_access_token()

    def after_delete(self, node, user):
        self.deauthorize(Auth(user=user), add_log=True, save=True)

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
