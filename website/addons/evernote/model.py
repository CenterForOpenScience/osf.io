# -*- coding: utf-8 -*-

from framework.exceptions import HTTPError
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import exceptions
from website.addons.base import StorageAddonBase
from website.addons.evernote import (settings, utils)
from website.addons.evernote.serializer import EvernoteSerializer
from website.oauth.models import (ExternalProvider, OAUTH1)

from framework.auth import Auth

from modularodm import fields

import logging
logger = logging.getLogger(__name__)

class Evernote(ExternalProvider):

    name = 'Evernote'
    short_name = 'evernote'

    # Evernote has a sandbox and a production service
    # with different endpoints

    client_id = settings.EVERNOTE_CLIENT_ID
    client_secret = settings.EVERNOTE_CLIENT_SECRET

    auth_url_base = '{}/OAuth.action'.format(settings.BASE_URL)
    request_token_url = '{}/oauth'.format(settings.BASE_URL)
    callback_url = '{}/oauth'.format(settings.BASE_URL)

    _oauth_version = OAUTH1

    def handle_callback(self, response):

        client = utils.get_evernote_client(token=response.get('oauth_token'))

        userStore = client.get_user_store()
        user = userStore.getUser()

        return {
            'provider_id': user.id,
            'display_name': user.name,
            'profile_url': ''
        }

class EvernoteUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = Evernote
    serializer = EvernoteSerializer

class EvernoteNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = Evernote
    serializer = EvernoteSerializer

    folder_id = fields.StringField(default=None)
    folder_name = fields.StringField()
    folder_path = fields.StringField()

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Evernote(self.external_account)
        return self._api

    def set_user_auth(self, user_settings):

        self.user_settings = user_settings
        self.nodelogger.log(action='node_authorized', save=True)

    def set_folder(self, folder_id, auth):

        self.folder_id = str(folder_id)
        client = utils.get_evernote_client(self.external_account.oauth_key)
        _folder_data = utils.get_notebook(client, self.folder_id)
        self.folder_name = _folder_data['name']
        self.folder_path = _folder_data['name']
        self.save()

        if not self.complete:
            self.user_settings.grant_oauth_access(
                node=self.owner,
                external_account=self.external_account,
                metadata={'folder': self.folder_id}
            )
            self.user_settings.save()

        self.nodelogger.log(action='folder_selected', save=True)

    def fetch_full_folder_path(self):

        return self.folder_path

    def fetch_folder_name(self):

        return self.folder_path

    def clear_settings(self):
        self.folder_id = None
        self.folder_name = None
        self.folder_path = None

    def deauthorize(self, auth=None, add_log=True):
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
            return {'token': self.external_account.oauth_key}
        except Exception as error:
            raise HTTPError(str(error), data={'message_long': error.message})

    def serialize_waterbutler_settings(self):
        if self.folder_id is None:
            raise exceptions.AddonError('Folder is not configured')
        return {'folder': self.folder_id}

    ##### Callback overrides #####
    def after_delete(self, node=None, user=None):
        self.deauthorize(Auth(user=user), add_log=True)
        self.save()

    def on_delete(self):
        self.deauthorize(add_log=False)
        self.save()

