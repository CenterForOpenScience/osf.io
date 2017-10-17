# -*- coding: utf-8 -*-
import pytest
import unittest
import mock
from nose.tools import assert_equal

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


class ZoteroUserSettingsTestCase(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    short_name = 'zotero'
    full_name = 'Zotero'
    ExternalAccountFactory = ZoteroAccountFactory
