# -*- coding: utf-8 -*-
from framework.exceptions import PermissionsError

from website.addons.base import AddonUserSettingsBase

from modularodm import fields

from website.addons.base import AddonNodeSettingsBase
from website.oauth.models import ExternalProvider
from pyzotero import zotero

from website.addons.citations.utils import serialize_folder

from . import settings

class ZoteroUserSettings(AddonUserSettingsBase):

    def _get_connected_accounts(self):
        """Get user's connected Zotero accounts"""
        return [
            x for x in self.owner.external_accounts if x.provider == 'zotero'
        ]

    def grant_oauth_access(self, node, external_account, metadata=None):
        metadata = metadata or {}

        # create an entry for the node, if necessary
        if node._id not in self.oauth_grants:
            self.oauth_grants[node._id] = {}

        # create an entry for the external account on the node, if necessary
        if external_account._id not in self.oauth_grants[node._id]:
            self.oauth_grants[node._id][external_account._id] = {}

        # update the metadata with the supplied values
        for key, value in metadata.iteritems():
            self.oauth_grants[node._id][external_account._id][key] = value

        self.save()

    def verify_oauth_access(self, node, external_account, metadata=None):
        metadata = metadata or {}

        # ensure the grant exists
        try:
            grants = self.oauth_grants[node._id][external_account._id]
        except KeyError:
            return False

        # Verify every key/value pair is in the grants dict
        for key, value in metadata.iteritems():
            if key not in grants or grants[key] != value:
                return False

        return True

    def to_json(self, user):
        rv = super(ZoteroUserSettings, self).to_json(user)
        rv['accounts'] = [
            {
                'id': account._id,
                'provider_id': account.provider_id,
                'display_name': account.display_name,
            } for account in self._get_connected_accounts()
        ]
        return rv

class ZoteroNodeSettings(AddonNodeSettingsBase):
    external_account = fields.ForeignField('externalaccount',
                                           backref='connected')

    zotero_list_id = fields.StringField()

    # Keep track of all user settings that have been associated with this
    #   instance. This is so OAuth grants can be checked, even if the grant is
    #   not currently being used.
    user_settings = fields.ForeignField('zoterousersettings')

    _api = None

    @property
    def api(self):
        """authenticated ExternalProvider instance"""
        if self._api is None:
            self._api = Zotero()
            self._api.account = self.external_account
        return self._api

    @property
    def has_auth(self):
        if not (self.user_settings and self.external_account):
            return False

        return self.user_settings.verify_oauth_access(
            node=self.owner,
            external_account=self.external_account
        )

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

    def set_auth(self, external_account, user):
        """Connect the node addon to a user's external account.
        """
        # external account must be the user's
        if external_account not in user.external_accounts:
            raise PermissionsError("Invalid ExternalAccount for User")

        # tell the user's addon settings that this node is connected to it
        user_settings = user.get_or_add_addon('zotero')
        user_settings.grant_oauth_access(
            node=self.owner,
            external_account=external_account
            # no metadata, because the node has access to no folders
        )
        user_settings.save()

        # update this instance
        self.user_settings = user_settings
        self.external_account = external_account

        # ensure no list is associated, as we're attaching new credentials.
        self.zotero_list_id = None

        self.save()

    def clear_auth(self):
        """Disconnect the node settings from the user settings"""

        self.external_account = None
        self.zotero_list_id = None
        self.user_settings = None
        self.save()

    def set_target_folder(self, zotero_list_id):
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

    def citation_lists(self, extract_folder):
        """List of CitationList objects, derived from Zotero collections"""
        client = self.client

        collections = client.collections()

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
            while more:
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
        while more:
            page = self.client.items(content='csljson', limit=100, start=offset)
            citations = citations + page
            if len(page) == 0 or len(page) < 100:
                more = False
            else:
                offset = offset + len(page)
        return citations
