# -*- coding: utf-8 -*-

from modularodm import fields
from pyzotero import zotero, zotero_errors

from framework.exceptions import HTTPError

from website.addons.base import AddonOAuthUserSettingsBase
from website.addons.zotero.serializer import ZoteroSerializer
from website.addons.zotero import settings
from website.citations.models import AddonCitationsNodeSettings
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

    def handle_callback(self, response):

        return {
            'display_name': response['username'],
            'provider_id': response['userID'],
            'profile_url': 'https://zotero.org/users/{}/'.format(
                response['userID']
            ),
        }

    def _get_folders(self):
        """Get a list of a user's folders"""
        client = self.client

        # Note: Pagination is the only way to ensure all of the collections
        #       are retrieved. 100 is the limit per request. This applies
        #       to Mendeley too, though that limit is 500.
        return client.collections(limit=100)

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

    def _folder_metadata(self, folder_id):
        collection = self.client.collection(folder_id)
        return collection

    def _citations_for_folder(self, list_id):
        """Get all the citations in a specified collection

        :param  str list_id: ID for a Zotero collection.
        :return list of csljson objects representing documents.
        """
        citations = []
        more = True
        offset = 0
        while more and len(citations) <= MAX_CITATION_LOAD:
            page = self.client.collection_items(list_id, content='csljson', size=100, start=offset)
            citations = citations + page
            if len(page) == 0 or len(page) < 100:
                more = False
            else:
                offset = offset + len(page)
        return citations

    def _citations_for_user(self):
        """Get all the citations from the user """
        citations = []
        more = True
        offset = 0
        while more and len(citations) <= MAX_CITATION_LOAD:
            page = self.client.items(content='csljson', limit=100, start=offset)
            citations = citations + page
            if len(page) == 0 or len(page) < 100:
                more = False
            else:
                offset = offset + len(page)
        return citations


class ZoteroUserSettings(AddonOAuthUserSettingsBase):
    oauth_provider = Zotero
    serializer = ZoteroSerializer


class ZoteroNodeSettings(AddonCitationsNodeSettings):
    provider_name = 'zotero'
    oauth_provider = Zotero
    serializer = ZoteroSerializer

    list_id = fields.StringField()
    _api = None

    @property
    def _fetch_folder_name(self):
        folder = self.api._folder_metadata(self.list_id)
        return folder['data'].get('name')
