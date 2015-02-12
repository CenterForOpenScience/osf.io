# -*- coding: utf-8 -*-

from website.addons.base import AddonUserSettingsBase

from modularodm import fields

from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.oauth.models import ExternalProvider
from pyzotero import zotero


# TODO: Move to utilities @jmcarp
def serialize_folder(name, account_id, list_id=None):
    return {
        'name': name,
        'provider_account_id': account_id,
        'provider_list_id': list_id,
    }


class AddonZoteroUserSettings(AddonUserSettingsBase):

    def _get_connected_accounts(self):
        """Get user's connected Zotero accounts"""
        return [
            x for x in self.owner.external_accounts if x.provider == 'zotero'
        ]

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


def serialize_account(account):
    return {
        'id': account._id,
        'provider_id': account.provider_id,
        'display_name': account.display_name,
    }


class AddonZoteroNodeSettings(AddonNodeSettingsBase):
    external_account = fields.ForeignField('externalaccount',
                                           backref='connected')

    zotero_list_id = fields.StringField()

    # Keep track of all user settings that have been associated with this
    #   instance. This is so OAuth grants can be checked, even if the grant is
    #   not currently being used.
    associated_user_settings = fields.AbstractForeignField(list=True)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Zotero()
            self._api.account = self.external_account
        return self._api

    def grant_oauth_access(self, user, external_account, metadata=None):
        """Grant OAuth access, updates metadata on user settings
        :param User user:
        :param ExternalAccount external_account:
        :param dict metadata:
        """
        user_settings = user.get_addon('zotero')

        # associate the user settings with this node's settings
        if user_settings not in self.associated_user_settings:
            self.associated_user_settings.append(user_settings)

        user_settings.grant_oauth_access(
            node=self.owner,
            external_account=external_account,
            metadata=metadata
        )

        user_settings.save()

    def verify_oauth_access(self, external_account, list_id):
        """Determine if access to the ExternalAccount has been granted
        :param ExternalAccount external_account:
        :param str list_id: ID of the Zotero list requested
        :return bool: True or False
        """
        for user_settings in self.associated_user_settings:
            try:
                granted = user_settings[self.owner._id][external_account._id]
            except KeyError:
                # no grant for this node, move along
                continue

            if list_id in granted.get('lists', []):
                return True
        return False
    
    def to_json(self, user):
        accounts = {
            account for account
            in user.external_accounts
            if account.provider == 'zotero'
        }
        if self.external_account:
            accounts.add(self.external_account)

        ret = super(AddonZoteroNodeSettings, self).to_json(user)
        ret['accounts'] = [serialize_account(each) for each in accounts]
        ret['list_id'] = self.zotero_list_id
        ret['current_account'] = (
            serialize_account(self.external_account)
            if self.external_account
            else None
        )

        return ret


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
        _userID = response['userID']
        return {
            'provider_id': _userID,
            'display_name': response['username']
        }

    @property
    def client(self):
        """An API session with Zotero"""
        if not self._client:
            self._client = zotero.Zotero(self.account.provider_id, 'user', self.account.oauth_key)
        return self._client

    @property
    def citation_lists(self):
        """List of CitationList objects, derived from Zotero collections"""
        client = self.client

        collections = client.collections()

        all_documents = serialize_folder(
            'All Documents',
            account_id=self.account.provider_id,
        )

        serialized_folders = [
            serialize_folder(
                each['data']['name'],
                account_id=self.account.provider_id,
                list_id=each['data']['key'],
            )
            for each in collections
        ]

        return [all_documents] + serialized_folders

    def get_zotero_list(self, list_id=None):
        """Get a single CitationList

        :param str list_id: ID for a Zotero collection. Optional.
        :return CitationList: CitationList for the collection, or for all documents
        """
        collection = self.client.collection(list_id) if list_id else None
        collection_items = self.client.collection_items(list_id, content='csljson') if list_id else None

        if collection:
            return self._citations_for_zotero_collection(collection_items)
        return self._citations_for_zotero_user()

    def _citations_for_zotero_collection(self, collection):
        """Get all the citations in a specified collection

        :param  csljson collection: list of csljson documents
        :return list of citation objects representing said dicts of said documents.
        """
        return collection

    def _citations_for_zotero_user(self):
        """Get all the citations from the user """
        return self.client.items(content='csljson')
