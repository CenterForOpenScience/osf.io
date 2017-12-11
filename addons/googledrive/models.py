# -*- coding: utf-8 -*-
"""Persistence layer for the google drive addon.
"""
import os

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from framework.auth import Auth
from framework.exceptions import HTTPError
from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from addons.base import exceptions
from addons.googledrive import settings as drive_settings
from addons.googledrive.client import (GoogleAuthClient,
                                               GoogleDriveClient)
from addons.googledrive.serializer import GoogleDriveSerializer
from addons.googledrive.utils import to_hgrid
from website.util import api_v2_url

# from website.files.models.ext import PathFollowingFileNode


# TODO make googledrive "pathfollowing"
# A migration will need to be run that concats
# folder_path and filenode.path
# class GoogleDriveFileNode(PathFollowingFileNode):
class GoogleDriveFileNode(BaseFileNode):
    _provider = 'googledrive'
    FOLDER_ATTR_NAME = 'folder_path'


class GoogleDriveFolder(GoogleDriveFileNode, Folder):
    pass


class GoogleDriveFile(GoogleDriveFileNode, File):
    @property
    def _hashes(self):
        try:
            return {'md5': self._history[-1]['extra']['hashes']['md5']}
        except (IndexError, KeyError):
            return None


class GoogleDriveProvider(ExternalProvider):
    name = 'Google Drive'
    short_name = 'googledrive'

    client_id = drive_settings.CLIENT_ID
    client_secret = drive_settings.CLIENT_SECRET

    auth_url_base = '{}{}'.format(drive_settings.OAUTH_BASE_URL, 'auth?access_type=offline&approval_prompt=force')
    callback_url = '{}{}'.format(drive_settings.API_BASE_URL, 'oauth2/v3/token')
    auto_refresh_url = callback_url
    refresh_time = drive_settings.REFRESH_TIME
    expiry_time = drive_settings.EXPIRY_TIME

    default_scopes = drive_settings.OAUTH_SCOPE
    _auth_client = GoogleAuthClient()
    _drive_client = GoogleDriveClient()

    def handle_callback(self, response):
        client = self._auth_client
        info = client.userinfo(response['access_token'])
        return {
            'provider_id': info['sub'],
            'display_name': info['name'],
            'profile_url': info.get('profile', None)
        }

    def fetch_access_token(self, force_refresh=False):
        self.refresh_oauth_key(force=force_refresh)
        return self.account.oauth_key


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = GoogleDriveProvider
    serializer = GoogleDriveSerializer


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = GoogleDriveProvider
    provider_name = 'googledrive'

    folder_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    serializer = GoogleDriveSerializer
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    _api = None

    @property
    def api(self):
        """Authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = GoogleDriveProvider(self.external_account)
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        ))

    @property
    def folder_name(self):
        if not self.folder_id:
            return None

        if self.folder_path != '/':
            return os.path.split(self.folder_path)[1]
        else:
            return '/ (Full Google Drive)'

    def clear_settings(self):
        self.folder_id = None
        self.folder_path = None

    def get_folders(self, **kwargs):
        node = self.owner

        #  Defaults exist when called by the API, but are `None`
        path = kwargs.get('path') or ''
        folder_id = kwargs.get('folder_id') or 'root'

        try:
            access_token = self.fetch_access_token()
        except exceptions.InvalidAuthError:
            raise HTTPError(403)

        client = GoogleDriveClient(access_token)
        if folder_id == 'root':
            about = client.about()

            return [{
                'addon': self.config.short_name,
                'path': '/',
                'kind': 'folder',
                'id': about['rootFolderId'],
                'name': '/ (Full Google Drive)',
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/googledrive/folders/'.format(self.owner._id),
                        params={
                            'path': '/',
                            'id': about['rootFolderId']
                    })
                }
            }]

        contents = [
            to_hgrid(item, node, path=path)
            for item in client.folders(folder_id)
        ]
        return contents

    def set_folder(self, folder, auth):
        """Configure this addon to point to a Google Drive folder

        :param dict folder:
        :param User user:
        """
        self.folder_id = folder['id']
        self.folder_path = folder['path']

        # Tell the user's addon settings that this node is connecting
        self.user_settings.grant_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        )  # Performs a save on self.user_settings
        self.save()

        self.nodelogger.log('folder_selected', save=True)

    @property
    def selected_folder_name(self):
        if self.folder_id is None:
            return ''
        elif self.folder_id == 'root':
            return 'Full Google Drive'
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
        if not self.folder_id:
            raise exceptions.AddonError('Folder is not configured')

        return {
            'folder': {
                'id': self.folder_id,
                'name': self.folder_name,
                'path': self.folder_path
            }
        }

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for('addon_view_or_download_file', path=metadata['path'], provider='googledrive')

        self.owner.add_log(
            'googledrive_{0}'.format(action),
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': self.folder_path,

                'urls': {
                    'view': url,
                    'download': url + '?action=download'
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
