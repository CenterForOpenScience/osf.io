# -*- coding: utf-8 -*-

from modularodm import fields
from pyzotero import zotero, zotero_errors

from framework.exceptions import HTTPError

from website.addons.base import AddonOAuthNodeSettingsBase
from website.addons.base import AddonOAuthUserSettingsBase
from website.addons.citations.utils import serialize_folder
from website.addons.zotero import serializer
from website.addons.zotero import settings
from website.oauth.models import ExternalProvider

# TODO: Don't cap at 200 responses. We can only fetch 100 citations at a time. With lots
# of citations, requesting the citations may take longer than the UWSGI harakiri time.
# For now, we load 200 citations max and show a message to the user.
MAX_CITATION_LOAD = 200

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

        return {
            'display_name': response['username'],
            'provider_id': response['userID'],
            'profile_url': 'https://zotero.org/users/{}/'.format(
                response['userID']
            ),
        }

    @property
    def client(self):
        """An API session with Zotero"""

        if not self._client:
            self._client = zotero.Zotero(self.account.provider_id, 'user', self.account.oauth_key)

            # Check if Zotero can be accessed with current credentials
            try:
                self._client.collections()
            except zotero_errors.PyZoteroError as err:
                self._client = None
                if isinstance(err, zotero_errors.UserNotAuthorised):
                    raise HTTPError(403)
                else:
                    raise err

        return self._client

    def citation_lists(self, extract_folder):
        """List of CitationList objects, derived from Zotero collections"""

        client = self.client

        # Note: Pagination is the only way to ensure all of the collections
        #       are retrieved. 100 is the limit per request. This applies
        #       to Mendeley too, though that limit is 500.
        collections = client.collections(limit=100)

        all_documents = serialize_folder(
            'All Documents',
            id='ROOT',
            parent_id='__'
        )

        serialized_folders = [
            extract_folder(each)
            for each in collections
        ]

        return [all_documents] + serialized_folders

    def _folder_metadata(self, folder_id):
        collection = self.client.collection(folder_id)
        return collection

    def get_list(self, list_id=None):
        """Get a single CitationList

        :param str list_id: ID for a Zotero collection. Optional.
        :return CitationList: CitationList for the collection, or for all documents
        """
        if list_id == 'ROOT':
            list_id = None

        if list_id:
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
            return self._citations_for_zotero_collection(citations)
        else:
            return self._citations_for_zotero_user()

    def _citations_for_zotero_collection(self, collection):
        """Get all the citations in a specified collection

        :param  csljson collection: list of csljson documents
        :return list of citation objects representing said dicts of said documents.
        """
        return collection

    def _citations_for_zotero_user(self):
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
    serializer = serializer.ZoteroSerializer


class ZoteroNodeSettings(AddonOAuthNodeSettingsBase):
    oauth_provider = Zotero
    serializer = serializer.ZoteroSerializer

    zotero_list_id = fields.StringField()

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Zotero()
            self._api.account = self.external_account
        return self._api

    @property
    def complete(self):
        return self.has_auth and self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': self.zotero_list_id},
        )

    @property
    def selected_folder_name(self):
        if self.zotero_list_id is None:
            return ''
        elif self.zotero_list_id != 'ROOT':
            folder = self.api._folder_metadata(self.zotero_list_id)
            return folder['data'].get('name')
        else:
            return 'All Documents'

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
        return 'zotero'

    @property
    def folder_id(self):
        return self.zotero_list_id

    @property
    def folder_name(self):
        return self.selected_folder_name

    @property
    def folder_path(self):
        return self.selected_folder_name

    def set_auth(self, *args, **kwargs):
        self.zotero_list_id = None
        return super(ZoteroNodeSettings, self).set_auth(*args, **kwargs)

    def clear_auth(self):
        self.zotero_list_id = None
        return super(ZoteroNodeSettings, self).clear_auth()

    def deauthorize(self, auth=None, add_log=True):
        """Remove user authorization from this node and log the event."""
        if add_log:
            self.owner.add_log(
                'zotero_node_deauthorized',
                params={
                    'project': self.owner.parent_id,
                    'node': self.owner._id,
                },
                auth=auth,
            )

        self.clear_auth()

        self.save()

    def set_target_folder(self, zotero_list_id, zotero_list_name, auth):
        """Configure this addon to point to a Zotero folder

        :param str zotero_list_id:
        :param ExternalAccount external_account:
        :param User user:
        """

        # Tell the user's addon settings that this node is connecting
        self.user_settings.grant_oauth_access(
            node=self.owner,
            external_account=self.external_account,
            metadata={'folder': zotero_list_id}
        )
        self.user_settings.save()

        # update this instance
        self.zotero_list_id = zotero_list_id
        self.save()

        self.owner.add_log(
            'zotero_folder_selected',
            params={
                'project': self.owner.parent_id,
                'node': self.owner._id,
                'folder_id': zotero_list_id,
                'folder_name': zotero_list_name,
            },
            auth=auth,
        )
