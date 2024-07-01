from rest_framework import status as http_status
import logging
import os

from addons.base.models import (BaseOAuthNodeSettings, BaseOAuthUserSettings,
                                BaseStorageAddon)
from django.db import models
from dropbox import Dropbox
from dropbox.exceptions import ApiError, DropboxException
from dropbox.files import FolderMetadata
from furl import furl
from framework.auth import Auth
from framework.exceptions import HTTPError
from osf.models.external import ExternalProvider
from osf.models.files import File, Folder, BaseFileNode
from osf.utils.fields import ensure_str
from addons.base import exceptions
from addons.dropbox import settings
from addons.dropbox.serializer import DropboxSerializer
from website.util import api_v2_url

logger = logging.getLogger(__name__)


class DropboxFileNode(BaseFileNode):
    _provider = 'dropbox'


class DropboxFolder(DropboxFileNode, Folder):
    pass


class DropboxFile(DropboxFileNode, File):
    @property
    def _hashes(self):
        try:
            return {'Dropbox content_hash': self._history[-1]['extra']['hashes']['dropbox']}
        except (IndexError, KeyError):
            return None


class Provider(ExternalProvider):
    name = 'Dropbox'
    short_name = 'dropbox'

    client_id = settings.DROPBOX_KEY
    client_secret = settings.DROPBOX_SECRET

    auth_url_base = settings.DROPBOX_OAUTH_AUTH_ENDPOINT
    callback_url = settings.DROPBOX_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = settings.DROPBOX_OAUTH_TOKEN_ENDPOINT
    refresh_time = settings.REFRESH_TIME

    @property
    def auth_url(self):
        # Dropbox requires explicitly requesting refresh_tokens via `token_access_type`
        # https://developers.dropbox.com/oauth-guide#implementing-oauth
        url = super().auth_url
        return furl(url).add({'token_access_type': 'offline'}).url

    def handle_callback(self, response):
        access_token = response['access_token']
        self.client = Dropbox(access_token)
        info = self.client.users_get_current_account()
        return {
            'key': access_token,
            'provider_id': info.account_id,
            'display_name': info.name.display_name,
        }

    def fetch_access_token(self, force_refresh=False):
        self.refresh_oauth_key(force=force_refresh)
        return ensure_str(self.account.oauth_key)


class UserSettings(BaseOAuthUserSettings):
    """Stores user-specific dropbox information.
    token.
    """
    oauth_provider = Provider
    serializer = DropboxSerializer

    def revoke_remote_oauth_access(self, external_account):
        """Overrides default behavior during external_account deactivation.

        Tells Dropbox to remove the grant for the OSF associated with this account.
        """
        client = Dropbox(Provider(external_account).fetch_access_token())
        try:
            client.auth_token_revoke()
        except DropboxException:
            pass


class NodeSettings(BaseOAuthNodeSettings, BaseStorageAddon):
    oauth_provider = Provider
    serializer = DropboxSerializer

    folder = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Provider(self.external_account)
        return self._api

    @property
    def folder_id(self):
        return self.folder

    @property
    def folder_name(self):
        return os.path.split(self.folder or '')[1] or '/ (Full Dropbox)' if self.folder else None

    @property
    def folder_path(self):
        return self.folder

    @property
    def display_name(self):
        return f'{self.config.full_name}: {self.folder}'

    def fetch_access_token(self):
        return self.api.fetch_access_token()

    def clear_settings(self):
        self.folder = None

    def get_folders(self, **kwargs):
        folder_id = kwargs.get('folder_id')
        if folder_id is None:
            return [{
                'addon': 'dropbox',
                'id': '/',
                'path': '/',
                'kind': 'folder',
                'name': '/ (Full Dropbox)',
                'urls': {
                    'folders': api_v2_url(f'nodes/{self.owner._id}/addons/dropbox/folders/', params={'id': '/'})
                }
            }]

        client = Dropbox(self.fetch_access_token())

        try:
            folder_id = '' if folder_id == '/' else folder_id
            list_folder = client.files_list_folder(folder_id)
            contents = [x for x in list_folder.entries]
            while list_folder.has_more:
                list_folder = client.files_list_folder_continue(list_folder.cursor)
                contents += [x for x in list_folder.entries]
        except ApiError as error:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': error.user_message_text,
                'message_long': error.user_message_text,
            })
        except DropboxException:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

        return [
            {
                'addon': 'dropbox',
                'kind': 'folder',
                'id': item.path_display,
                'name': item.path_display.split('/')[-1],
                'path': item.path_display,
                'urls': {
                    'folders': api_v2_url(
                        f'nodes/{self.owner._id}/addons/dropbox/folders/', params={'id': item.path_display}
                    )
                }
            }
            for item in contents
            if isinstance(item, FolderMetadata)
        ]

    def set_folder(self, folder, auth):
        self.folder = folder
        # Add log to node
        self.nodelogger.log(action='folder_selected', save=True)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        folder = self.folder
        self.clear_settings()

        if add_log:
            extra = {'folder': folder}
            self.nodelogger.log(action='node_deauthorized', extra=extra, save=True)

        self.clear_auth()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fetch_access_token()}

    def serialize_waterbutler_settings(self):
        if not self.folder:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder}

    def create_waterbutler_log(self, auth, action, metadata):
        url = self.owner.web_url_for(
            'addon_view_or_download_file',
            path=metadata['path'].strip('/'),
            provider='dropbox'
        )
        self.owner.add_log(
            f'dropbox_{action}',
            auth=auth,
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'path': metadata['path'],
                'folder': self.folder,
                'urls': {
                    'view': url,
                    'download': url + '?action=download'
                },
            },
        )

    def __repr__(self):
        return f'<NodeSettings(node_id={self.owner._primary_key!r})>'

    ##### Callback overrides #####
    def after_delete(self, user):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()
