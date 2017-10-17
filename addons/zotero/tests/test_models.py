# -*- coding: utf-8 -*-
import pytest
import unittest
import mock
from framework.auth import Auth
from nose.tools import (assert_equal, assert_is_none, assert_true)

from addons.base.tests.utils import MockFolder, MockLibrary

from pyzotero.zotero_errors import UserNotAuthorised

from addons.base.tests.models import (
    CitationAddonProviderTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin,
    OAuthCitationsNodeSettingsTestSuiteMixin,
)
from addons.zotero.models import (
    Zotero, NodeSettings,
)
from addons.zotero.tests.factories import (
    ZoteroAccountFactory,
    ZoteroNodeSettingsFactory,
    ZoteroUserSettingsFactory,
)

from addons.zotero.provider import ZoteroCitationsProvider

pytestmark = pytest.mark.django_db

class ZoteroProviderTestCase(CitationAddonProviderTestSuiteMixin, unittest.TestCase):

    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = Zotero
    ApiExceptionClass = UserNotAuthorised

    def test_handle_callback(self):
        response = {
            'userID': 'Fake User ID',
            'username': 'Fake User Name',
        }

        res = self.provider.handle_callback(response)

        assert(res.get('display_name') == 'Fake User Name')
        assert(res.get('provider_id') == 'Fake User ID')

    def test_citation_lists_from_personal_library(self):
        # mock_library_client doesn't need to specified b/c personal libraries
        # use the client.
        mock_client = mock.Mock()
        mock_folders = [MockFolder()]
        mock_list = mock.Mock()
        mock_list.items = mock_folders
        mock_client.folders.list.return_value = mock_list
        mock_client.collections.return_value = mock_folders
        self.provider._client = mock_client
        mock_account = mock.Mock()
        self.provider.account = mock_account
        res = self.provider.citation_lists(self.ProviderClass()._extract_folder, "personal")
        assert_equal(res[1]['name'], mock_folders[0].name)
        assert_equal(res[1]['id'], mock_folders[0].json['id'])

    def test_citation_lists_from_group_library(self):
        mock_library_client = mock.Mock()
        mock_folders = [MockFolder()]
        mock_list = mock.Mock()
        mock_list.items = mock_folders
        mock_library_client.folders.list.return_value = mock_list
        mock_library_client.collections.return_value = mock_folders
        self.provider._library_client = mock_library_client
        mock_account = mock.Mock()
        self.provider.account = mock_account
        res = self.provider.citation_lists(self.ProviderClass()._extract_folder, "Test Group")
        assert_equal(res[1]['name'], mock_folders[0].name)
        assert_equal(res[1]['id'], mock_folders[0].json['id'])



class ZoteroNodeSettingsTestCase(OAuthCitationsNodeSettingsTestSuiteMixin, unittest.TestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ProviderClass = ZoteroCitationsProvider
    OAuthProviderClass = Zotero
    ExternalAccountFactory = ZoteroAccountFactory

    NodeSettingsFactory = ZoteroNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = ZoteroUserSettingsFactory

    def setUp(self):
        super(ZoteroNodeSettingsTestCase, self).setUp()
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': 'fake_folder_id', 'library': 'fake_library_id'}
        )
        self.user_settings.save()

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'list_id': 'fake_folder_id',
            'library_id': 'fake_library_id',
            'owner': self.node
        }

    def test_fetch_library_name_personal(self):
        self.node_settings.library_id = 'personal'

        assert_equal(
            self.node_settings.fetch_library_name,
            'My library'
        )

    def test_selected_library_name_empty(self):
        self.node_settings.library_id = None

        assert_equal(
            self.node_settings.fetch_library_name,
            ''
        )

    def test_selected_library_name(self):
        # Mock the return from api call to get the library's name
        mock_library = MockLibrary()
        name = None

        with mock.patch.object(self.OAuthProviderClass, '_library_metadata', return_value=mock_library):
            name = self.node_settings.fetch_library_name

        assert_equal(
            name,
            'Fake Library'
        )

    def test_set_library(self):
        folder_id = 'fake-folder-id'
        folder_name = 'fake-folder-name'
        library_id = 'fake-library-id'
        library_name = 'fake-library-name'

        self.node_settings.clear_settings()
        self.node_settings.save()
        self.node_settings.list_id = folder_id
        self.node_settings.save()
        assert_equal(self.node_settings.list_id, folder_id)

        provider = self.ProviderClass()

        provider.set_config(
            self.node_settings,
            self.user,
            folder_id,
            folder_name,
            Auth(user=self.user),
            library_id,
            library_name,
        )

        # instance was updated
        assert_equal(
            self.node_settings.library_id,
            'fake-library-id',
        )
        # If library_id is being set, the folder_id is cleared.
        assert_equal(
            self.node_settings.list_id,
            None,
        )

        # user_settings was updated
        # TODO: the call to grant_oauth_access should be mocked
        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account,
                metadata={'library': 'fake-library-id'}
            )
        )

        log = self.node.logs.latest()
        assert_equal(log.action, '{}_library_selected'.format(self.short_name))
        assert_equal(log.params['library_id'], library_id)
        assert_equal(log.params['library_name'], library_name)



class ZoteroUserSettingsTestCase(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
