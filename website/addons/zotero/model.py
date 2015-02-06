from website.addons.base import AddonUserSettingsBase
import time

from modularodm import fields
from modularodm import Q


from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.addons.base import AddonUserSettingsBase
from website.citations.models import Citation
from website.citations.models import CitationList
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

        collections = client.collections()

        return (
            self._zotero_collection_to_citation_list(collection)
            for collection in collections
        )

    def _zotero_collection_to_citation_list(self, collection):
        return CitationList(
            name=collection['data']['name'],
            provider_account_id=self.account.provider_id,
            provider_list_id=collection['data']['key']
        )

    def get_list(self, list_id=None):
        """Get a single CitationList

        :param str list_id: ID for a Zotero collection. Optional.
        :return CitationList: CitationList for the collection, or for all documents
        """

        collection = self.client.collection(list_id) if list_id else None
        if collection:
            citations = lambda: self._citations_for_zotero_collection(collection)
        else:
            citations = lambda: self._citations_for_zotero_user()

        citation_list = CitationList(
            name=collection['data']['name'] if collection else self.account.display_name,
            provider_account_id=self.account.provider_id,
            provider_list_id=list_id,
            citations=citations,
        )
        return citation_list

    def _citations_for_zotero_collection(self, collection):
        return [
            self._citation_for_zotero_document(document)
            for document in collection
        ]

    def _citations_for_zotero_user(self):
        return [
            self._citation_for_zotero_document(document)
            for document in self.client.items()
        ]

    def _citation_for_zotero_document(self, document):
        csl = document['data']
        return Citation(**csl)

    def _citation_for_zotero_document2(self, document):
        """Zotero document to ``website.citations.models.Citation``

        :param BaseDocument document:
            An instance of ``zotero.models.base_document.BaseDocument``
        :return Citation:
        """
        csl = {
            'id': document['key'],
            'type': document['data']['itemType']
        }

        if document['data']['title']:
            csl['title'] = document['data']['title']

        if document.json.get('authors'):
            csl['author'] = [
                {
                    'given': person.get('first_name'),
                    'family': person.get('last_name'),
                } for person in document.json.get('authors')
            ]

        if document.json.get('source'):
            csl['source'] = document.json.get('source')

        if document.year:
            csl['issued'] = {'date-parts': [[document.year]]}


        # gather identifiers
        idents = document.json.get('identifiers')
        if idents is not None:
            if idents.get('isbn'):
                csl['ISBN'] = idents.get('isbn')
            if idents.get('issn'):
                csl['ISSN'] = idents.get('issn')
            if idents.get('pmid'):
                csl['PMID'] = idents.get('pmid')
            if idents.get('doi'):
                csl['DOI'] = idents.get('doi')

        return Citation(**csl)
