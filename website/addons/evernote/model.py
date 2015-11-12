
from website.addons.base import AddonUserSettingsBase, AddonNodeSettingsBase
from website.addons.base import StorageAddonBase
from website.addons.evernote import settings
from website.oauth.models import (ExternalProvider, OAUTH1)


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
        """
        Placeholder:
        I don't think this callback does anything meaningful yet
        in the absence of a way to store the auth token.
        """

        return {
            'provider_id': "[provider_id]",
            'display_name': "[display_name]",
            'profile_url': "https://example.com/profile_url",
        }

class EvernoteUserSettings(AddonUserSettingsBase):
    oauth_provider = Evernote


class EvernoteNodeSettings(StorageAddonBase, AddonNodeSettingsBase):
    pass
