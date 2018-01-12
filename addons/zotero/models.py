# -*- coding: utf-8 -*-

from addons.base.models import BaseCitationsNodeSettings, BaseOAuthUserSettings
from django.db import models
from framework.exceptions import HTTPError
from pyzotero import zotero, zotero_errors
from addons.zotero import \
    settings  # TODO: Move `settings` to `apps.py` when deleting
from addons.zotero.serializer import ZoteroSerializer
from website.citations.providers import CitationsOauthProvider

# TODO: Don't cap at 200 responses. We can only fetch 100 citations at a time. With lots
# of citations, requesting the citations may take longer than the UWSGI harakiri time.
# For now, we load 200 citations max and show a message to the user.
MAX_CITATION_LOAD = 200

class Zotero(CitationsOauthProvider):
    name = 'Zotero'
    short_name = 'zotero'
    _oauth_version = 1

    client_id = settings.ZOTERO_CLIENT_ID
    client_secret = settings.ZOTERO_CLIENT_SECRET

    auth_url_base = 'https://www.zotero.org/oauth/authorize'
    callback_url = 'https://www.zotero.org/oauth/access'
    request_token_url = 'https://www.zotero.org/oauth/request'
    default_scopes = ['all']

    serializer = ZoteroSerializer
    _library_client = None

    def handle_callback(self, response):

        return {
            'display_name': response['username'],
            'provider_id': response['userID'],
            'profile_url': 'https://zotero.org/users/{}/'.format(
                response['userID']
            ),
        }

    def citation_lists(self, extract_folder, library_id=None):
        """
        List of CitationList objects, derived from Mendeley folders

        Modified to add library_id to arguments, because folders are going
        to be loaded from library (either personal library or one of group libraries)
        """
        # TODO: Verify OAuth access to each folder
        all_documents = self.serializer.serialized_root_folder

        serialized_folders = [
            extract_folder(each)
            for each in self._get_folders(library_id)
        ]
        return [all_documents] + serialized_folders

    def get_list(self, list_id=None, library_id=None):
        """Get a single CitationList
        :param str list_id: ID for a folder. Optional.
        :param str list_id: ID for library. Optional.
        :return CitationList: CitationList for the folder, or for all documents
        """
        if not list_id or list_id == 'ROOT':
            return self._citations_for_user(library_id)

        return self._citations_for_folder(list_id, library_id)

    def _get_folders(self, library_id=None):
        """
        Get a list of a user's folders, either from the personal library,
        or a group library, if specified
        """
        client = self._get_library(library_id)

        # Note: Pagination is the only way to ensure all of the collections
        #       are retrieved. 100 is the limit per request. This applies
        #       to Mendeley too, though that limit is 500.
        return client.collections(limit=100)

    def _get_library(self, library_id):
        """
        If library id specified, fetch the group library from Zotero. Otherwise, use
        the user's personal library.
        """
        if library_id and library_id != 'personal':
            if not self._library_client:
                self._library_client = zotero.Zotero(str(library_id), 'group', self.account.oauth_key)
            return self._library_client
        else:
            return self.client

    def _get_client(self):
        return zotero.Zotero(self.account.provider_id, 'user', self.account.oauth_key)

    def _verify_client_validity(self):
        # Check if Zotero can be accessed with current credentials
        try:
            self._client.collections()
        except zotero_errors.PyZoteroError as err:
            self._client = None
            if isinstance(err, zotero_errors.UserNotAuthorised):
                raise HTTPError(403)
            else:
                raise err

    def _fetch_libraries(self, limit, start):
        """
        Retrieves the Zotero library data to which the current library_id and api_key has access
        """
        total_libraries = self.client._totals('/users/{u}/groups')
        libraries = self.client.groups(limit=limit, start=start, sort='title')
        libraries.append(total_libraries)
        return libraries

    def _folder_metadata(self, folder_id, library_id=None):
        client = self._get_library(library_id)
        return client.collection(folder_id)

    def _library_metadata(self, library_id):
        for library in self.client.groups():
            if str(library['id']) == library_id:
                return library
        return None

    def _citations_for_folder(self, list_id, library_id=None):
        """Get all the citations in a specified collection

        :param  str list_id: ID for a Zotero collection.
        :return list of csljson objects representing documents.
        """
        client = self._get_library(library_id)

        citations = []
        more = True
        offset = 0
        while more and len(citations) <= MAX_CITATION_LOAD:
            page = client.collection_items(list_id, content='csljson', limit=100, start=offset)
            citations = citations + page
            if len(page) == 0 or len(page) < 100:
                more = False
            else:
                offset = offset + len(page)
        return citations

    def _citations_for_user(self, library_id=None):
        """Get all the citations from the user """
        citations = []
        more = True
        offset = 0
        client = self._get_library(library_id)

        while more and len(citations) <= MAX_CITATION_LOAD:
            page = client.items(content='csljson', limit=100, start=offset)
            citations = citations + page
            if len(page) == 0 or len(page) < 100:
                more = False
            else:
                offset = offset + len(page)
        return citations

    @property
    def auth_url(self):
        """
        Add all_groups query param so Zotero API key will have permissions to user's groups
        """
        url = super(Zotero, self).auth_url
        return url + '&all_groups=read'


class UserSettings(BaseOAuthUserSettings):
    oauth_provider = Zotero
    serializer = ZoteroSerializer


class NodeSettings(BaseCitationsNodeSettings):
    provider_name = 'zotero'
    oauth_provider = Zotero
    serializer = ZoteroSerializer
    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    list_id = models.TextField(blank=True, null=True)
    library_id = models.TextField(blank=True, null=True)
    _api = None

    @property
    def complete(self):
        """
        Boolean indication of addon completeness
        Requires that both library_id and list_id have been defined.
        """
        return bool(self.has_auth and self.list_id and self.library_id and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.list_id, 'library': self.library_id},
        ))

    @property
    def fetch_library_name(self):
        """Returns a displayable library name"""
        if self.library_id is None:
            return ''
        else:
            if self.library_id == 'personal':
                return 'My library'
            library = self.api._library_metadata(self.library_id)
            return library['data'].get('name') if library else 'My library'

    @property
    def _fetch_folder_name(self):
        folder = self.api._folder_metadata(self.list_id, self.library_id)
        return folder['data'].get('name')

    def clear_settings(self):
        """Clears selected folder and selected library configuration"""
        self.list_id = None
        self.library_id = None
