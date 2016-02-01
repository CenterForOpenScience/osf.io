# -*- coding: utf-8 -*-

import time

import mendeley
from mendeley.exception import MendeleyApiException
from modularodm import fields

from website.addons.base import AddonOAuthUserSettingsBase
from website.addons.mendeley.serializer import MendeleySerializer
from website.addons.mendeley import settings
from website.addons.mendeley.api import APISession
from website.oauth.models import ExternalProvider
from website.citations.models import AddonCitationsNodeSettings
from website.util import web_url_for

from framework.exceptions import HTTPError

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
        client = self.client(credentials=response)

        # make a second request for the Mendeley user's ID and name
        profile = client.profiles.me

        return {
            'provider_id': profile.id,
            'display_name': profile.display_name,
            'profile_url': profile.link,
        }

    def _get_folders(self):
        """Get a list of a user's folders"""

        client = self.client

        return client.folders.list().items

    @property
    def client(self, credentials=None):
        """An API session with Mendeley"""
        if not self._client:
            partial = mendeley.Mendeley(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=web_url_for('oauth_callback',
                                         service_name='mendeley',
                                         _absolute=True),
            )
            credentials = credentials or {
                'access_token': self.account.oauth_key,
                'refresh_token': self.account.refresh_token,
                'expires_at': time.mktime(self.account.expires_at.timetuple()),
                'token_type': 'bearer',
            }
            self._client = APISession(partial, credentials)

            #Check if Mendeley can be accessed
            try:
                self._client.folders.list()
            except MendeleyApiException as error:
                self._client = None
                if error.status == 403:
                    raise HTTPError(403)
                else:
                    raise HTTPError(error.status)

        return self._client

    def citation_lists(self, extract_folder):
        """List of CitationList objects, derived from Mendeley folders"""

        folders = self._get_folders()
        # TODO: Verify OAuth access to each folder
        all_documents = MendeleySerializer.serialized_root_folder

        serialized_folders = [
            extract_folder(each)
            for each in folders
        ]
        return [all_documents] + serialized_folders

    def get_list(self, list_id='ROOT'):
        """Get a single CitationList
        :param str list_id: ID for a Mendeley folder. Optional.
        :return CitationList: CitationList for the folder, or for all documents
        """
        if list_id == 'ROOT':
            folder = None
        else:
            folder = self.client.folders.get(list_id)

        if folder:
            return self._citations_for_mendeley_folder(folder)
        return self._citations_for_mendeley_user()

    def _folder_metadata(self, folder_id):
        folder = self.client.folders.get(folder_id)
        return folder

    def _citations_for_mendeley_folder(self, folder):

        document_ids = [
            document.id
            for document in folder.documents.iter(page_size=500)
        ]
        citations = {
            citation['id']: citation
            for citation in self._citations_for_mendeley_user()
        }
        return map(lambda id: citations[id], document_ids)

    def _citations_for_mendeley_user(self):

        documents = self.client.documents.iter(page_size=500)
        return [
            self._citation_for_mendeley_document(document)
            for document in documents
        ]

    def _citation_for_mendeley_document(self, document):
        """Mendeley document to ``website.citations.models.Citation``
        :param BaseDocument document:
            An instance of ``mendeley.models.base_document.BaseDocument``
        :return Citation:
        """
        csl = {
            'id': document.json.get('id')
        }

        CSL_TYPE_MAP = {
            'book_section': 'chapter',
            'case': 'legal_case',
            'computer_program': 'article',
            'conference_proceedings': 'paper-conference',
            'encyclopedia_article': 'entry-encyclopedia',
            'film': 'motion_picture',
            'generic': 'article',
            'hearing': 'speech',
            'journal': 'article-journal',
            'magazine_article': 'article-magazine',
            'newspaper_article': 'article-newspaper',
            'statute': 'legislation',
            'television_broadcast': 'broadcast',
            'web_page': 'webpage',
            'working_paper': 'report'
        }

        csl_type = document.json.get('type')

        if csl_type in CSL_TYPE_MAP:
            csl['type'] = CSL_TYPE_MAP[csl_type]

        else:
            csl['type'] = 'article'

        if document.json.get('abstract'):
            csl['abstract'] = document.json.get('abstract')

        if document.json.get('accessed'):
            csl['accessed'] = document.json.get('accessed')

        if document.json.get('authors'):
            csl['author'] = [
                {
                    'given': person.get('first_name'),
                    'family': person.get('last_name'),
                } for person in document.json.get('authors')
            ]

        if document.json.get('chapter'):
            csl['chapter-number'] = document.json.get('chapter')

        if document.json.get('city') and document.json.get('country'):
            csl['publisher-place'] = document.json.get('city') + ", " + document.json.get('country')

        elif document.json.get('city'):
            csl['publisher-place'] = document.json.get('city')

        elif document.json.get('country'):
            csl['publisher-place'] = document.json.get('country')

        if document.json.get('edition'):
            csl['edition'] = document.json.get('edition')

        if document.json.get('editors'):
            csl['editor'] = [
                {
                    'given': person.get('first_name'),
                    'family': person.get('last_name'),
                } for person in document.json.get('editors')
            ]

        if document.json.get('genre'):
            csl['genre'] = document.json.get('genre')

        # gather identifiers
        idents = document.json.get('identifiers')
        if idents is not None:
            if idents.get('doi'):
                csl['DOI'] = idents.get('doi')
            if idents.get('isbn'):
                csl['ISBN'] = idents.get('isbn')
            if idents.get('issn'):
                csl['ISSN'] = idents.get('issn')
            if idents.get('pmid'):
                csl['PMID'] = idents.get('pmid')

        if document.json.get('issue'):
            csl['issue'] = document.json.get('issue')

        if document.json.get('language'):
            csl['language'] = document.json.get('language')

        if document.json.get('medium'):
            csl['medium'] = document.json.get('medium')

        if document.json.get('pages'):
            csl['page'] = document.json.get('pages')

        if document.json.get('publisher'):
            csl['publisher'] = document.json.get('publisher')

        if csl_type == 'thesis':
            csl['publisher'] = document.json.get('institution')

        if document.json.get('revision'):
            csl['number'] = document.json.get('revision')

        if document.json.get('series'):
            csl['collection-title'] = document.json.get('series')

        if document.json.get('series_editor'):
            csl['collection-editor'] = document.json.get('series_editor')

        if document.json.get('short_title'):
            csl['shortTitle'] = document.json.get('short_title')

        if document.json.get('source'):
            csl['container-title'] = document.json.get('source')

        if document.json.get('title'):
            csl['title'] = document.json.get('title')

        if document.json.get('volume'):
            csl['volume'] = document.json.get('volume')

        urls = document.json.get('websites', [])
        if urls:
            csl['URL'] = urls[0]

        if document.json.get('year'):
            csl['issued'] = {'date-parts': [[document.json.get('year')]]}

        return csl


class MendeleyUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = Mendeley
    serializer = MendeleySerializer


class MendeleyNodeSettings(AddonCitationsNodeSettings):
    provider_name = 'mendeley'
    oauth_provider = Mendeley
    serializer = MendeleySerializer

    list_id = fields.StringField()
    _api = None

    @property
    def _fetch_folder_name(self):
        folder = self.api._folder_metadata(self.list_id)
        return folder.name
