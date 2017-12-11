import httplib as http
import logging
import os

import requests
from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from box import BoxClient, CredentialsV2
from box.client import BoxClientException
from django.db import models
from framework.auth import Auth
from framework.exceptions import HTTPError
from oauthlib.oauth2 import InvalidGrantError
from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from urllib3.exceptions import MaxRetryError
from addons.base import exceptions
from addons.box import settings
from addons.box.serializer import BoxSerializer
from website.util import api_v2_url

logger = logging.getLogger(__name__)


class BoxFileNode(BaseFileNode):
    _provider = 'box'


class BoxFolder(BoxFileNode, Folder):
    pass


class BoxFile(BoxFileNode, File):
    @property
    def _hashes(self):
        try:
            return {'sha1': self._history[-1]['extra']['hashes']['sha1']}
        except (IndexError, KeyError):
            return None


class Provider(ExternalProvider):
    name = 'Box'
    short_name = 'box'

    client_id = settings.BOX_KEY
    client_secret = settings.BOX_SECRET

    auth_url_base = settings.BOX_OAUTH_AUTH_ENDPOINT
    callback_url = settings.BOX_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = callback_url
    refresh_time = settings.REFRESH_TIME
    expiry_time = settings.EXPIRY_TIME
    default_scopes = ['root_readwrite']

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new UserSettings
        record to the user and saves the user's access token and account info.
        """

        client = BoxClient(CredentialsV2(
            response['access_token'],
            response['refresh_token'],
            settings.BOX_KEY,
            settings.BOX_SECRET,
        ))

        about = client.get_user_info()

        return {
            'provider_id': about['id'],
            'display_name': about['name'],
            'profile_url': 'https://app.box.com/profile/{0}'.format(about['id'])
        }


class UserSettings(BaseOAuthUserSettings):
    """Stores user-specific box information
    """

    oauth_provider = Provider
    serializer = BoxSerializer

    def revoke_remote_oauth_access(self, external_account):
        try:
            # TODO: write client for box, stop using third-party lib
            requests.request(
                'POST',
                settings.BOX_OAUTH_REVOKE_ENDPOINT,
                params={
                    'client_id': settings.BOX_KEY,
                    'client_secret': settings.BOX_SECRET,
                    'token': external_account.oauth_key,
                }
            )
        except requests.HTTPError:
            pass


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = Provider
    serializer = BoxSerializer

    folder_id = models.TextField(null=True, blank=True)
    folder_name = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Provider(self.external_account)
        return self._api

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder_id)

    def fetch_full_folder_path(self):
        return self.folder_path

    def get_folders(self, **kwargs):
        folder_id = kwargs.get('folder_id')
        if folder_id is None:
            return [{
                'id': '0',
                'path': '/',
                'addon': 'box',
                'kind': 'folder',
                'name': '/ (Full Box)',
                'urls': {
                    # 'folders': node.api_url_for('box_folder_list', folderId=0),
                    'folders': api_v2_url('nodes/{}/addons/box/folders/'.format(self.owner._id),
                        params={'id': '0'}
                    )
                }
            }]

        try:
            Provider(self.external_account).refresh_oauth_key()
            client = BoxClient(self.external_account.oauth_key)
        except BoxClientException:
            raise HTTPError(http.FORBIDDEN)

        try:
            metadata = client.get_folder(folder_id)
        except BoxClientException:
            raise HTTPError(http.NOT_FOUND)
        except MaxRetryError:
            raise HTTPError(http.BAD_REQUEST)

        # Raise error if folder was deleted
        if metadata.get('is_deleted'):
            raise HTTPError(http.NOT_FOUND)

        folder_path = '/'.join(
            [
                x['name']
                for x in metadata['path_collection']['entries']
            ] + [metadata['name']]
        )

        return [
            {
                'addon': 'box',
                'kind': 'folder',
                'id': item['id'],
                'name': item['name'],
                'path': os.path.join(folder_path, item['name']).replace('All Files', ''),
                'urls': {
                    'folders': api_v2_url('nodes/{}/addons/box/folders/'.format(self.owner._id),
                        params={'id': item['id']}
                    )
                }
            }
            for item in metadata['item_collection']['entries']
            if item['type'] == 'folder'
        ]

    def set_folder(self, folder_id, auth):
        self.folder_id = str(folder_id)
        self.folder_name, self.folder_path = self._folder_data(folder_id)
        self.nodelogger.log(action='folder_selected', save=True)

    def _folder_data(self, folder_id):
        # Split out from set_folder for ease of testing, due to
        # outgoing requests. Should only be called by set_folder
        try:
            Provider(self.external_account).refresh_oauth_key(force=True)
        except InvalidGrantError:
            raise exceptions.InvalidAuthError()
        try:
            client = BoxClient(self.external_account.oauth_key)
            folder_data = client.get_folder(self.folder_id)
        except BoxClientException:
            raise exceptions.InvalidFolderError()

        folder_name = folder_data['name'].replace('All Files', '') or '/ (Full Box)'
        folder_path = '/'.join(
            [x['name'] for x in folder_data['path_collection']['entries'] if x['name']] +
            [folder_data['name']]
        ).replace('All Files', '') or '/'

        return folder_name, folder_path

    def clear_settings(self):
        self.folder_id = None
        self.folder_name = None
        self.folder_path = None

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        folder_id = self.folder_id
        self.clear_settings()

        if add_log:
            extra = {'folder_id': folder_id}
            self.nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.clear_auth()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        try:
            Provider(self.external_account).refresh_oauth_key()
            return {'token': self.external_account.oauth_key}
        except BoxClientException as error:
            raise HTTPError(error.status_code, data={'message_long': error.message})

    def serialize_waterbutler_settings(self):
        if self.folder_id is None:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder_id}

    def create_waterbutler_log(self, auth, action, metadata):
        self.owner.add_log(
            'box_{0}'.format(action),
            auth=auth,
            params={
                'path': metadata['materialized'],
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_id,
                'urls': {
                    'view': self.owner.web_url_for('addon_view_or_download_file',
                        provider='box',
                        action='view',
                        path=metadata['path']
                    ),
                    'download': self.owner.web_url_for('addon_view_or_download_file',
                        provider='box',
                        action='download',
                        path=metadata['path']
                    ),
                },
            },
        )

    ##### Callback overrides #####
    def after_delete(self, node=None, user=None):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
