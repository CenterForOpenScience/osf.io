
from website.addons.base import AddonOAuthUserSettingsBase, AddonOAuthNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.addons.evernote import (settings, utils)
from website.addons.evernote.serializer import EvernoteSerializer
from website.oauth.models import (ExternalProvider, OAUTH1)

from evernote.api.client import EvernoteClient

import logging
logger = logging.getLogger(__name__)

class Evernote(ExternalProvider):
    """
    First cut at the Evernote provider

    """
    name = 'Evernote'
    short_name = 'evernote'

    # Evernote has a sandbox and a production service
    # with different endpoints

    client_id = settings.EVERNOTE_CLIENT_ID
    client_secret = settings.EVERNOTE_CLIENT_SECRET
    _sandbox = settings.EVERNOTE_SANDBOX

    BASE_URL = "https://www.evernote.com" if not _sandbox  \
           else "https://sandbox.evernote.com"

    auth_url_base = '{}/OAuth.action'.format(BASE_URL)
    request_token_url = '{}/oauth'.format(BASE_URL)
    callback_url = '{}/oauth'.format(BASE_URL)

    _oauth_version = OAUTH1


    def handle_callback(self, response):
        """View called when the Oauth flow is completed. Adds a new BoxUserSettings
        record to the user and saves the user's access token and account info.
        """

        client = utils.get_evernote_client(token=response.get('oauth_token'))

        userStore = client.get_user_store()
        user = userStore.getUser()

        return {
            'provider_id': '',
            'display_name': user.username,
            'profile_url': ''
        }

class EvernoteUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = Evernote
    serializer = EvernoteSerializer


class EvernoteNodeSettings(StorageAddonBase, AddonOAuthNodeSettingsBase):
    oauth_provider = Evernote
