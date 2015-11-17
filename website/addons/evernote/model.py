
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.addons.evernote import settings
from website.oauth.models import (ExternalProvider, OAUTH1)

from evernote.api.client import EvernoteClient

# S=s1:U=91b44:E=1586dfd0344:C=151164bd418:P=1cd:A=en-devtoken:V=2:H=ac1412837aeac699e0826380baf0be3d

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

        client =  EvernoteClient(
            consumer_key=settings.EN_CONSUMER_KEY,
            consumer_secret=settings.EN_CONSUMER_SECRET,
            sandbox=settings.EVERNOTE_SANDBOX
        )

        userStore = client.get_user_store()
        user = userStore.getUser()

        return {
            'provider_id': '',
            'display_name': user.username,
            'profile_url': ''
        }

class EvernoteUserSettings(AddonUserSettingsBase):
    oauth_provider = Evernote


class EvernoteNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
    oauth_provider = Evernote
