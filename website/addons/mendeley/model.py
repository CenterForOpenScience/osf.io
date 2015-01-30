import time

import mendeley
from mendeley.session import MendeleySession

from website import settings
from website.addons.base import AddonUserSettingsBase
from website.citations import Citation
from website.citations import CitationList
from website.oauth.models import ExternalProvider


class AddonMendeleyUserSettings(AddonUserSettingsBase):
    pass


class Mendeley(ExternalProvider):
    name = "Mendeley"
    short_name = "mendeley"

    client_id = settings.MENDELEY_CLIENT_ID
    client_secret = settings.MENDELEY_CLIENT_SECRET

    auth_url_base = 'https://api.mendeley.com/oauth/authorize'
    callback_url = 'https://api.mendeley.com/oauth/token'
    default_scopes = ['all']

    _client = None

    def handle_callback(self, response):
        client = self._get_client(response)

        profile = client.profiles.me

        return {
            'provider_id': profile.id,
            'display_name': profile.display_name
        }

    def _get_client(self, credentials):
        if not self._client:
            partial = mendeley.Mendeley(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri='http://cos.ngrok.com/oauth/callback/mendeley/',
            )
            self._client = MendeleySession(partial, credentials)

        return self._client

    @property
    def client(self):
        if not self._client:
            self._client = self._get_client({
                'access_token': self.account.oauth_key,
                'refresh_token': self.account.refresh_token,
                'expires_at': time.mktime(self.account.expires_at.timetuple()),
                'token_type': 'bearer',
            })
        return self._client

    @property
    def citation_lists(self):
        client = self.client

        folders = client.folders.list().items

        return (
            self._mendeley_folder_to_citation_list(folder)
            for folder in folders
        )

    def _mendeley_folder_to_citation_list(self, folder):
        return CitationList(name=folder.name)