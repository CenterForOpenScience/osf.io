# -*- coding: utf-8 -*-
import os
import urllib

from modularodm import fields

from framework.auth import Auth
from framework.exceptions import HTTPError
from website.oauth.models import ExternalProvider

from website.addons.base import exceptions
from website.addons.base import StorageAddonBase
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase

from website.addons.onedrive import settings
from website.addons.onedrive.client import OneDriveClient
from website.addons.onedrive.utils import OneDriveNodeLogger
from website.addons.onedrive.serializer import OneDriveSerializer


class OneDrive(ExternalProvider):
    name = 'onedrive'
    short_name = 'onedrive'

    client_id = settings.ONEDRIVE_KEY
    client_secret = settings.ONEDRIVE_SECRET

    auth_url_base = settings.ONEDRIVE_OAUTH_AUTH_ENDPOINT
    callback_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    default_scopes = ['wl.basic wl.signin onedrive.readwrite wl.offline_access']

    expiry_time = settings.REFRESH_TIME

    _drive_client = OneDriveClient()

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new OneDriveUserSettings
        record to the user and saves the user's access token and account info.
        """
        userInfo = self._drive_client.user_info_for_token(response['access_token'])

        return {
            'provider_id': userInfo['id'],
            'display_name': userInfo['name'],
            'profile_url': userInfo['link']
        }

    def fetch_access_token(self, force_refresh=False):
        self.refresh_oauth_key(force=force_refresh)
        return self.account.oauth_key


class OneDriveUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific onedrive information
    """
    oauth_provider = OneDrive
    serializer = OneDriveSerializer


class OneDriveNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = OneDrive
    serializer = OneDriveSerializer

    foreign_user_settings = fields.ForeignField(
        'onedriveusersettings', backref='authorized'
    )
    folder_id = fields.StringField(default=None)
    folder_path = fields.StringField()

    _folder_data = None

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = OneDrive(self.external_account)
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

        if self.folder_path != '/':
            # `urllib` does not properly handle unicode.
            # encode input to `str`, decode output back to `unicode`
            return urllib.unquote(os.path.split(self.folder_path)[1].encode('utf-8')).decode('utf-8')
        else:
            return '/ (Full OneDrive)'

    def fetch_folder_name(self):
        return self.folder_name

    def clear_settings(self):
        self.folder_id = None
        self.folder_path = None

    def get_folder(self, **kwargs):
        node = self.owner

        #  Defaults exist when called by the API, but are `None`
        # path = kwargs.get('path') or ''
        folder_id = kwargs.get('folder_id') or 'root'

        if folder_id is None:
            return [{
                'id': '0',
                'path': 'All Files',
                'addon': 'onedrive',
                'kind': 'folder',
                'name': '/ (Full OneDrive)',
                'urls': {
                    'folders': node.api_url_for('onedrive_folder_list', folderId=0),
                }
            }]

        if folder_id == '0':
            folder_id = 'root'

        try:
            access_token = self.fetch_access_token()
        except exceptions.InvalidAuthError:
            raise HTTPError(403)

        oneDriveClient = OneDriveClient(access_token)
        items = oneDriveClient.folders(folder_id)

        return [
            {
                'addon': 'onedrive',
                'kind': 'folder',
                'id': item['id'],
                'name': item['name'],
                'path': item['name'],
                'urls': {
                    'folders': node.api_url_for('onedrive_folder_list', folderId=item['id']),
                }
            }
            for item in items
        ]

    def set_folder(self, folder, auth):
        self.folder_id = folder['id']
        self.folder_path = folder['name']
        self.save()

        if not self.complete:
            self.user_settings.grant_oauth_access(
                node=self.owner,
                external_account=self.external_account,
                metadata={'folder': self.folder_id}
            )
            self.user_settings.save()

        # Add log to node
        nodelogger = OneDriveNodeLogger(node=self.owner, auth=auth)  # AddonOAuthNodeSettingsBase.nodelogger(self)
        nodelogger.log(action='folder_selected', save=True)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        node = self.owner

        if add_log:
            extra = {'folder_id': self.folder_id}
            nodelogger = OneDriveNodeLogger(node=node, auth=auth)
            nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.folder_id = None
        self._update_folder_data()
        self.clear_auth()

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
                'path': metadata['materialized'],
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_path,
                'urls': {
                    'view': self.owner.web_url_for('addon_view_or_download_file', provider='onedrive', action='view', path=metadata['path']),
                    'download': self.owner.web_url_for('addon_view_or_download_file', provider='onedrive', action='download', path=metadata['path']),
                },
            },
        )

    def fetch_access_token(self):
        return self.api.fetch_access_token()

    ##### Callback overrides #####
    def after_delete(self, node=None, user=None):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.clear_auth()
        self.save()
