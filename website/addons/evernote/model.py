
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

    auth_url_base = '{}/OAuth.action'.format(settings.BASE_URL)
    request_token_url = '{}/oauth'.format(settings.BASE_URL)
    callback_url = '{}/oauth'.format(settings.BASE_URL)

    _oauth_version = OAUTH1

    def handle_callback(self, response):

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

    # based on https://github.com/CenterForOpenScience/osf.io/blob/4a5d4e5a887c944174694300c42b399638184722/website/addons/box/model.py#L105-L107
    def fetch_full_folder_path(self):
        # don't know why this would be needed for Evernote

        return self.folder_path
