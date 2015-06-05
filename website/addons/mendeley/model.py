# -*- coding: utf-8 -*-

import time

from urlparse import parse_qs

import mendeley
from modularodm import fields

from website.addons.base import AddonOAuthNodeSettingsBase
from website.addons.base import AddonOAuthUserSettingsBase
from website.addons.citations.utils import serialize_folder
from website.addons.mendeley import serializer
from website.addons.mendeley import settings
from website.addons.mendeley.api import APISession
from website.oauth.models import ExternalProvider
from website.util import web_url_for


class Mendeley(ExternalProvider):
    name = 'Mendeley'
    short_name = 'mendeley'

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
            'display_name': profile.display_name,
            'profile_url': profile.link,
        }

    def _get_client(self, credentials):
        if not self._client:
            partial = mendeley.Mendeley(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=web_url_for('oauth_callback',
                                         service_name='mendeley',
                                         _absolute=True),
            )
            self._client = APISession(partial, credentials)

        return self._client

    def _get_folders(self):
        """Get a list of a user's folders"""

        client = self.client

        return client.folders.list().items

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

    def citation_lists(self, extract_folder):
        """List of CitationList objects, derived from Mendeley folders"""

        folders = self._get_folders()
        # TODO: Verify OAuth access to each folder
        all_documents = serialize_folder(
            'All Documents',
            id='ROOT',
            parent_id='__'
        )
        serialized_folders = [
            extract_folder(each)
            for each in folders
        ]
        return [all_documents] + serialized_folders

    def _marker_from_page(self, page):
        if page is None:
            return None
        next_link = page.rsp.links.get('next')
        if next_link is None:
            return None
        link = next_link['url']
        qs = link.split('?')[-1]
        return parse_qs(qs).get('marker')

    def get_list(self, list_id='ROOT', next_page=None):
        """Get a single CitationList
        :param str list_id: ID for a Mendeley folder. Optional.
        :return CitationList: CitationList for the folder, or for all documents
        """
        if list_id == 'ROOT' or list_id is None:
            folder = None
        else:
            folder = self.client.folders.get(list_id)

        citations = None
        page = None
        if folder:
            citations, page = self._citations_for_mendeley_folder(folder, next_page)
        else:
            citations, page = self._citations_for_mendeley_user(next_page)
        marker = self._marker_from_page(page)
        return citations, marker

    def _folder_metadata(self, folder_id):
        folder = self.client.folders.get(folder_id)
        return folder

    def _citations_for_mendeley_folder(self, folder, next_page):
        documents = None
        if hasattr(next_page, 'next_page'):
            documents = next_page.next_page
        elif next_page is None:
            documents = folder.documents.list(page_size=100)
        else:
            documents = folder.documents.list(page_size=100, marker=next_page)

        document_ids = set([
            document.id
            for document in documents.items
        ])
        citations = {}
        next_page = None
        while set(document_ids).isdisjoint(citations.keys()):
            page, next_page = self._citations_for_mendeley_user(next_page, size=500)
            citations.update({
                citation['id']: citation
                for citation in page
            })
            if next_page is None:
                break
        return [citations[id] for id in document_ids], documents

    def _citations_for_mendeley_user(self, next_page, size=100):
        documents = None
        if hasattr(next_page, 'next_page'):
            documents = next_page.next_page
        elif next_page is None:
            documents = self.client.documents.list(page_size=size)
        else:
            documents = self.client.documents.list(page_size=size, marker=next_page)

        return [
            self._citation_for_mendeley_document(document)
            for document in documents.items
        ], documents

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

        urls = document.json.get('websites', [])
        if urls:
            csl['URL'] = urls[0]

        return csl


class MendeleyUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = Mendeley
    serializer = serializer.MendeleySerializer


class MendeleyNodeSettings(AddonOAuthNodeSettingsBase):
    oauth_provider = Mendeley
    serializer = serializer.MendeleySerializer

    mendeley_list_id = fields.StringField()

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Mendeley()
            self._api.account = self.external_account
        return self._api

    @property
    def complete(self):
        return bool(self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.mendeley_list_id},
        ))

    @property
    def selected_folder_name(self):
        if self.mendeley_list_id is None:
            return ''
        elif self.mendeley_list_id == 'ROOT':
            return 'All Documents'
        else:
            folder = self.api._folder_metadata(self.mendeley_list_id)
            return folder.name

    @property
    def root_folder(self):
        root = serialize_folder(
            'All Documents',
            id='ROOT',
            parent_id='__'
        )
        root['kind'] = 'folder'
        return root

    @property
    def provider_name(self):
        return 'mendeley'

    def clear_auth(self):
        self.mendeley_list_id = None
        return super(MendeleyNodeSettings, self).clear_auth()

    def set_auth(self, *args, **kwargs):
        self.mendeley_list_id = None
        return super(MendeleyNodeSettings, self).set_auth(*args, **kwargs)

    def set_target_folder(self, mendeley_list_id, mendeley_list_name, auth):
        """Configure this addon to point to a Mendeley folder

        :param str mendeley_list_id:
        :param ExternalAccount external_account:
        :param User user:
        """

        # Tell the user's addon settings that this node is connecting
        self.user_settings.grant_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': mendeley_list_id}
        )
        self.user_settings.save()

        # update this instance
        self.mendeley_list_id = mendeley_list_id
        self.save()

        self.owner.add_log(
            'mendeley_folder_selected',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder_id': mendeley_list_id,
                'folder_name': mendeley_list_name,
            },
            auth=auth,
        )
