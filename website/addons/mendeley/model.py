import time

import mendeley
from modularodm import fields


from website import settings
from website.addons.base import AddonNodeSettingsBase
from website.addons.base import AddonUserSettingsBase
from website.citations.models import Citation
from website.citations.models import CitationList
from website.oauth.models import ExternalProvider

from .api import APISession


class AddonMendeleyUserSettings(AddonUserSettingsBase):

    def _get_connected_accounts(self):
        """Get user's connected Mendeley accounts"""
        return [
            x for x in self.owner.external_accounts if x.provider == 'mendeley'
        ]

    def to_json(self, user):
        rv = super(AddonMendeleyUserSettings, self).to_json(user)
        rv['accounts'] = [
            {
                'id': account._id,
                'provider_id': account.provider_id,
                'display_name': account.display_name,
            } for account in self._get_connected_accounts()
        ]
        return rv


class AddonMendeleyNodeSettings(AddonNodeSettingsBase):
    external_account = fields.ForeignField('externalaccount',
                                           backref='connected')

    mendeley_list_id = fields.StringField()

    # Keep track of all user settings that have been associated with this
    #   instance. This is so OAuth grants can be checked, even if the grant is
    #   not currently being used.
    associated_user_settings = fields.AbstractForeignField(list=True)

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Mendeley()
            self._api.account = self.external_account
        return self._api

    def grant_oauth_access(self, user, external_account, metadata=None):
        """Grant OAuth access, updates metadata on user settings

        :param User user:
        :param ExternalAccount external_account:
        :param dict metadata:
        """
        user_settings = user.get_addon('mendeley')

        # associate the user settings with this node's settings
        if user_settings not in self.associated_user_settings:
            self.associated_user_settings.append(user_settings)

        user_settings.grant_oauth_access(
            node=self.owner,
            external_account=external_account,
            metadata=metadata,
        )

        user_settings.save()

    def verify_oauth_access(self, external_account, list_id):
        """Determine if access to the ExternalAccount has been granted

        :param ExternalAccount external_account:
        :param str list_id: ID of the Mendeley list requested
        :rtype bool:
        """
        for user_settings in self.associated_user_settings:
            try:
                granted = user_settings.oauth_grants[self.owner._id][external_account._id]
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
            if account.provider == 'mendeley'
        }
        if self.external_account:
            accounts.add(self.external_account)

        rv = super(AddonMendeleyNodeSettings, self).to_json(user)
        rv['accounts'] = [
            {
                'id': account._id,
                'provider_id': account.provider_id,
                'display_name': account.display_name,
            } for account in accounts
        ]

        return rv


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

        # make a second request for the Mendeley user's ID and name
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
            self._client = APISession(partial, credentials)

        return self._client

    @property
    def client(self):
        """An API session with Mendeley"""
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
        """List of CitationList objects, derived from Mendeley folders"""
        client = self.client

        folders = client.folders.list().items

        # TODO: Verify OAuth access to each folder

        # fake object to represent the user's whole account
        all_documents = [
            CitationList(
                name="All Documents",
                provider_list_id=None,
                provider_account_id=self.account.provider_id
            )
        ]

        return all_documents + [
            self._mendeley_folder_to_citation_list(folder)
            for folder in folders
        ]

    def get_list(self, list_id=None):
        """Get a single CitationList

        :param str list_id: ID for a Mendeley folder. Optional.
        :return CitationList: CitationList for the folder, or for all documents
        """
        folder = self.client.folders.get(list_id) if list_id else None
        if folder:
            citations = lambda: self._citations_for_mendeley_folder(folder)
        else:
            citations = lambda: self._citations_for_mendeley_user()

        citation_list = CitationList(
            name=folder.name if folder else self.account.display_name,
            provider_account_id=self.account.provider_id,
            provider_list_id=list_id,
            citations=citations,
        )

        return citation_list

    def _mendeley_folder_to_citation_list(self, folder):
        return CitationList(
            name=folder.name,
            provider_account_id=self.account.provider_id,
            provider_list_id=folder.json['id'],
        )

    def _citations_for_mendeley_folder(self, folder):
        return (
            self._citation_for_mendeley_document(document)
            for document in folder.documents.list().items
        )

    def _citations_for_mendeley_user(self):
        return (
            self._citation_for_mendeley_document(document)
            for document in self.client.documents.list().items
        )

    def _citation_for_mendeley_document(self, document):
        """Mendeley document to ``website.citations.models.Citation``

        :param BaseDocument document:
            An instance of ``mendeley.models.base_document.BaseDocument``
        :return Citation:
        """
        csl = {
            'id': document.json.get('id'),
            'type': document.json.get('type'),
        }

        if document.title:
            csl['title'] = document.title

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
