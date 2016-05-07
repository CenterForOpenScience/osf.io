# -*- coding: utf-8 -*-
import logging

from datetime import datetime

from modularodm import fields

from framework.auth import Auth
from framework.exceptions import HTTPError

from website.addons.base import exceptions
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase

from website.addons.onedrive import settings
from website.addons.onedrive.utils import OneDriveNodeLogger
from website.addons.onedrive.serializer import OneDriveSerializer
from website.addons.onedrive.client import OneDriveAuthClient
from website.addons.onedrive.client import OneDriveClient

from website.oauth.models import ExternalProvider

logger = logging.getLogger(__name__)

logging.getLogger('onedrive1').setLevel(logging.WARNING)


class OneDrive(ExternalProvider):
    name = 'onedrive'
    short_name = 'onedrive'

    client_id = settings.ONEDRIVE_KEY
    client_secret = settings.ONEDRIVE_SECRET

    auth_url_base = settings.ONEDRIVE_OAUTH_AUTH_ENDPOINT
    callback_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    auto_refresh_url = settings.ONEDRIVE_OAUTH_TOKEN_ENDPOINT
    default_scopes = ['wl.basic wl.signin onedrive.readwrite wl.offline_access']

    _auth_client = OneDriveAuthClient()
    _drive_client = OneDriveClient()

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new OneDriveUserSettings
        record to the user and saves the user's access token and account info.
        """
        userInfo = self._auth_client.user_info(response['access_token'])
        #  userInfo = userInfoRequest.json()
        logger.debug("userInfo:: %s", repr(userInfo))

        return {
            'provider_id': userInfo['id'],
            'display_name': userInfo['name'],
            'profile_url': userInfo['link']
        }

    def _refresh_token(self, access_token, refresh_token):
        """ Handles the actual request to refresh tokens

        :param str access_token: Access token (oauth key) associated with this account
        :param str refresh_token: Refresh token used to request a new access token
        :return dict token: New set of tokens
        """
        client = self._auth_client
        if refresh_token:
            token = client.refresh(access_token, refresh_token)
            return token
        else:
            return False

    def fetch_access_token(self, force_refresh=False):
        self.refresh_access_token(force=force_refresh)
        return self.account.oauth_key

    def refresh_access_token(self, force=False):
        """ If the token has expired or will soon, handles refreshing and the storage of new tokens

        :param bool force: Indicates whether or not to force the refreshing process, for the purpose of ensuring that authorization has not been unexpectedly removed.
        """
        if self._needs_refresh() or force:
            token = self._refresh_token(self.account.oauth_key, self.account.refresh_token)
            self.account.oauth_key = token['access_token']
            self.account.refresh_token = token['refresh_token']
            self.account.expires_at = datetime.utcfromtimestamp(token['expires_at'])
            self.account.save()

    def _needs_refresh(self):
        if self.account.expires_at is None:
            return False
        return (self.account.expires_at - datetime.utcnow()).total_seconds() < settings.REFRESH_TIME

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
    onedrive_id = fields.StringField(default=None)
    folder_name = fields.StringField()
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
    def display_name(self):
        return '{0}: {1}'.format(self.config.full_name, self.folder_name)

    @property
    def has_auth(self):
        """Whether an access token is associated with this node."""
        return bool(self.user_settings and self.user_settings.has_auth)

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
        ))

    def fetch_folder_name(self):
        self._update_folder_data()
        return self.folder_name.replace('All Files', '/ (Full OneDrive)')

    def fetch_full_folder_path(self):
        self._update_folder_data()
        return self.folder_path

    def _update_folder_data(self):
        if self.folder_id is None:
            return None

        logger.debug('self::' + repr(self))
        #request.json.get('selected')

        if not self._folder_data:
            self.path = self.folder_name
            self.save()

    def set_folder(self, folder, auth):
        self.folder_id = folder['name']
        self.onedrive_id = folder['id']
        self.folder_name = folder['name']
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
        nodelogger.log(action="folder_selected", save=True)

    def set_user_auth(self, user_settings):
        """Import a user's OneDrive authentication and create a NodeLog.

        :param OneDriveUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings
        nodelogger = OneDriveNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        nodelogger.log(action="node_authorized", save=True)

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        node = self.owner

        if add_log:
            extra = {'folder_id': self.folder_id}
            nodelogger = OneDriveNodeLogger(node=node, auth=auth)
            nodelogger.log(action="node_deauthorized", extra=extra, save=True)

        self.folder_id = None
        self._update_folder_data()
        self.user_settings = None
        self.clear_auth()

        self.save()

    def serialize_waterbutler_credentials(self):
        logger.debug("in serialize_waterbutler_credentials:: %s", repr(self))
        if not self.has_auth:
            raise exceptions.AddonError('Addon is not authorized')
        return {'token': self.fetch_access_token()}

    def serialize_waterbutler_settings(self):
        logger.debug("in serialize_waterbutler_settings:: {}".format(repr(self)))
        logger.debug('folder_id::{}'.format(self.folder_id))
        if self.folder_id is None:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.onedrive_id}

    def create_waterbutler_log(self, auth, action, metadata):
        self.owner.add_log(
            'onedrive_{0}'.format(action),
            auth=auth,
            params={
                'path': metadata['materialized'],
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder': self.folder_id,
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
