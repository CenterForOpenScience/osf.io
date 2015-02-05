from website.addons.base import AddonUserSettingsBase
import time

from modularodm import fields
from modularodm import Q


from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.addons.base import AddonUserSettingsBase
from website.citations import Citation
from website.citations import CitationList
from website.oauth.models import ExternalAccount
from website.oauth.models import ExternalProvider
from pyzotero import zotero

class AddonZoteroUserSettings(AddonUserSettingsBase):

    def _get_connected_accounts(self):
        return [x for x in self.owner.external_accounts if x.provider == 'zotero']

    def to_json(self, user):
        rv = super(AddonZoteroUserSettings, self).to_json(user)
        rv['accounts'] = [
            {
                'id': account._id,
                'provider_id': account.provider_id,
                'display_name': account.display_name,
            } for account in self._get_connected_accounts()
        ]
        return rv

class AddonZoteroNodeSettings(AddonNodeSettingsBase):
    external_account = fields.ForeignField('externalaccount',
                                           backref='connected')

    def to_json(self, user):
        accounts = {
            account for account
            in user.external_accounts
            if account.provider == 'zotero'
        }
        if self.external_account:
            accounts.add(self.external_account)

        rv = super(AddonZoteroNodeSettings, self).to_json(user)
        rv['accounts'] = [
            {
                'id': account._id,
                'provider_id': account.provider_id,
                'display_name': account.display_name,
            } for account in accounts
        ]

        return rv



class Zotero(ExternalProvider):
    name = "Zotero"
    short_name = "zotero"
    _oauth_version = 1

    client_id = settings.ZOTERO_CLIENT_ID
    client_secret = settings.ZOTERO_CLIENT_SECRET

    auth_url_base = 'https://www.zotero.org/oauth/authorize'
    callback_url = 'https://www.zotero.org/oauth/access'
    request_token_url = 'https://www.zotero.org/oauth/request'
    default_scopes = ['all']

    _client = None

    def handle_callback(self, response):
        _userID = response['userID'],
        return {
            'provider_id': _userID,
            'display_name': response['username']
        }

    def _get_client(self):
        if not self._client:
            self._client = zotero.Zotero(self.account.provider_id, 'user', self.account.oauth_key)
        return self._client

    @property
    def client(self):
        if not self._client:
            self._client = zotero.Zotero(self.account.provider_id, 'user', self.account.oauth_key)
        return self._client


    @property
    def citation_lists(self):
        client = self.client

        folders = client.collections()

        return (
            self._zotero_folder_to_citation_list(folder)
            for folder in folders
        )

    def _zotero_folder_to_citation_list(self, folder):
        return CitationList(
            name=folder['data']['name'],
            provider_account_id=self.account.provider_id,
            provider_list_id=folder['data']['key']
        )
