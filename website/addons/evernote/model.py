
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.addons.evernote import (settings, utils)
from website.addons.evernote.serializer import EvernoteSerializer
from website.oauth.models import (ExternalProvider, OAUTH1)

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
    #_sandbox = settings.EVERNOTE_SANDBOX

    auth_url_base = '{}/OAuth.action'.format(settings.BASE_URL)
    request_token_url = '{}/oauth'.format(settings.BASE_URL)
    callback_url = '{}/oauth'.format(settings.BASE_URL)

    _oauth_version = OAUTH1

    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new BoxUserSettings
        record to the user and saves the user's access token and account info.
        """

        client = utils.get_evernote_client(token=response.get('oauth_token'))

        userStore = client.get_user_store()
        user = userStore.getUser()

        return {
            'provider_id': user.id,  # or user.username
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

    # to hold data about current Notebook
    _folder_data = None

    def set_user_auth(self, user_settings):
        """Import a user's Evernote authentication and create a NodeLog.
        :param EvernoteUserSettings user_settings: The user settings to link.
        """
        self.user_settings = user_settings
        #nodelogger = BoxNodeLogger(node=self.owner, auth=Auth(user_settings.owner))
        #nodelogger.log(action="node_authorized", save=True)

    def set_folder(self, folder_id, auth):
        self.folder_id = str(folder_id)
        self._update_folder_data()
        self.save()

        if not self.complete:
            self.user_settings.grant_oauth_access(
                node=self.owner,
                external_account=self.external_account,
                metadata={'folder': self.folder_id}
            )
            self.user_settings.save()

        # Add log to node
        #nodelogger = BoxNodeLogger(node=self.owner, auth=auth)
        #nodelogger.log(action="folder_selected", save=True)

    def _update_folder_data(self):
        """
        given the folder_id, compute folder_name, folder_path
        """
        if self.folder_id is None:
            return None

        if not self._folder_data:
            try:
                # don't know whether we'll need to do something like this
                #refresh_oauth_key(self.external_account)
                client = utils.get_evernote_client(self.external_account.oauth_key)
                self._folder_data = utils.get_notebook(client, self.folder_id)
            except Exception:
                return

            self.folder_name = self._folder_data['name']
            self.folder_path = self._folder_data['name']

            self.save()

    # Sam C says following can be removed https://github.com/CenterForOpenScience/osf.io/pull/4670/files#r49327525
    # boilerplate from https://github.com/CenterForOpenScience/osf.io/blob/e4e1bd951b6e79d3bb2335d326bb44d9939bffb8/website/addons/box/model.py#L94-L99
    # @property
    # def complete(self):
    #     return bool(self.has_auth and self.user_settings.verify_oauth_access(
    #         node=self.owner,
    #         external_account=self.external_account,
    #     ))

    # based on https://github.com/CenterForOpenScience/osf.io/blob/4a5d4e5a887c944174694300c42b399638184722/website/addons/box/model.py#L105-L107
    def fetch_full_folder_path(self):
        # don't know why this would be needed for Evernote
        #self._update_folder_data()
        return self.folder_path
