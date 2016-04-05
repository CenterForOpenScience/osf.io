# -*- coding: utf-8 -*-
import logging

from box import CredentialsV2, BoxClient
from box.client import BoxClientException
from modularodm import fields
import requests

from framework.auth import Auth
from framework.exceptions import HTTPError

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.box import settings
from website.addons.box.serializer import BoxSerializer
from website.oauth.models import ExternalProvider

logger = logging.getLogger(__name__)


class Box(ExternalProvider):
    name = 'Box'
    short_name = 'box'

    client_id = settings.BOX_KEY
    client_secret = settings.BOX_SECRET

    auth_url_base = settings.BOX_OAUTH_AUTH_ENDPOINT
    callback_url = settings.BOX_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = callback_url
    refresh_time = settings.REFRESH_TIME
    default_scopes = ['root_readwrite']

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new BoxUserSettings
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


class BoxUserSettings(AddonOAuthUserSettingsBase):
    """Stores user-specific box information
    """
    oauth_provider = Box
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


class BoxNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):

    oauth_provider = Box
    serializer = BoxSerializer

    folder_id = fields.StringField(default=None)
    folder_name = fields.StringField()
    folder_path = fields.StringField()

    _folder_data = None

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Box(self.external_account)
        return self._api

    @property
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder_id)

    def fetch_folder_name(self):
        self._update_folder_data()
        return getattr(self, 'folder_name', '').replace('All Files', '/ (Full Box)')

    def fetch_full_folder_path(self):
        self._update_folder_data()
        return self.folder_path

    def _update_folder_data(self):
        if self.folder_id is None:
            return None

        if not self._folder_data:
            try:
                Box(self.external_account).refresh_oauth_key()
                client = BoxClient(self.external_account.oauth_key)
                self._folder_data = client.get_folder(self.folder_id)
            except BoxClientException:
                return

            self.folder_name = self._folder_data['name']
            self.folder_path = '/'.join(
                [x['name'] for x in self._folder_data['path_collection']['entries']]
                + [self._folder_data['name']]
            )
            self.save()

    def set_folder(self, folder_id, auth):
        self.folder_id = str(folder_id)
        self._update_folder_data()
        self.save()
        self.nodelogger.log(action="folder_selected", save=True)

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
            self.nodelogger.log(action="node_deauthorized", extra=extra, save=True)

        self._update_folder_data()
        self.clear_auth()

    def serialize_waterbutler_credentials(self):
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        try:
            Box(self.external_account).refresh_oauth_key()
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
                    'view': self.owner.web_url_for('addon_view_or_download_file', provider='box', action='view', path=metadata['path']),
                    'download': self.owner.web_url_for('addon_view_or_download_file', provider='box', action='download', path=metadata['path']),
                },
            },
        )

    ##### Callback overrides #####
    def after_delete(self, node=None, user=None):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.clear_auth()
        self.save()
