# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest
import unittest

from framework.auth import Auth
from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)

from addons.iqbrims.models import NodeSettings, IQBRIMSProvider
from addons.iqbrims.client import IQBRIMSClient, IQBRIMSAuthClient
from addons.iqbrims.tests.factories import (
    IQBRIMSAccountFactory,
    IQBRIMSNodeSettingsFactory,
    IQBRIMSUserSettingsFactory
)

pytestmark = pytest.mark.django_db

class TestIQBRIMSProvider(unittest.TestCase):
    def setUp(self):
        super(TestIQBRIMSProvider, self).setUp()
        self.provider = IQBRIMSProvider()

    @mock.patch.object(IQBRIMSAuthClient, 'userinfo')
    def test_handle_callback(self, mock_client):
        fake_response = {'access_token': 'abc123'}
        fake_info = {'sub': '12345', 'name': 'fakename', 'profile': 'fakeUrl'}
        mock_client.return_value = fake_info
        res = self.provider.handle_callback(fake_response)
        assert_equal(res['provider_id'], '12345')
        assert_equal(res['display_name'], 'fakename')
        assert_equal(res['profile_url'], 'fakeUrl')

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'iqbrims'
    full_name = 'IQB-RIMS'
    ExternalAccountFactory = IQBRIMSAccountFactory

    def setUp(self):
        super(TestUserSettings, self).setUp()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()

    def tearDown(self):
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        super(TestUserSettings, self).tearDown()


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'iqbrims'
    full_name = 'IQB-RIMS'
    ExternalAccountFactory = IQBRIMSAccountFactory

    NodeSettingsFactory = IQBRIMSNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = IQBRIMSUserSettingsFactory

    def setUp(self):
        self.mock_refresh = mock.patch.object(
            IQBRIMSProvider,
            'refresh_oauth_key'
        )
        self.mock_refresh.return_value = True
        self.mock_refresh.start()
        super(TestNodeSettings, self).setUp()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()

    def tearDown(self):
        self.mock_refresh.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        super(TestNodeSettings, self).tearDown()

    @mock.patch('addons.iqbrims.models.IQBRIMSProvider')
    def test_api_not_cached(self, mock_gdp):
        # The first call to .api returns a new object
        api = self.node_settings.api
        mock_gdp.assert_called_once()
        assert_equal(api, mock_gdp())

    @mock.patch('addons.iqbrims.models.IQBRIMSProvider')
    def test_api_cached(self, mock_gdp):
        # Repeated calls to .api returns the same object
        self.node_settings._api = 'testapi'
        api = self.node_settings.api
        assert_false(mock_gdp.called)
        assert_equal(api, 'testapi')

    def test_selected_folder_name_root(self):
        self.node_settings.folder_id = 'root'

        assert_equal(
            self.node_settings.selected_folder_name,
            'Full IQB-RIMS'
        )

    def test_selected_folder_name_empty(self):
        self.node_settings.folder_id = None

        assert_equal(
            self.node_settings.selected_folder_name,
            ''
        )

    ## Overrides ##

    def test_set_folder(self):
        folder = {
            'id': 'fake-folder-id',
            'name': 'fake-folder-name',
            'path': 'fake_path'
        }
        self.node_settings.set_folder(folder, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder_id, folder['id'])
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'folder':
            {
                'id': self.node_settings.folder_id,
                'name': self.node_settings.folder_name,
                'path': self.node_settings.folder_path,
            },
            'permissions':
            {
                u'チェックリスト': ['VISIBLE', 'WRITABLE'],
                u'スキャン結果': [],
                u'生データ': ['VISIBLE', 'WRITABLE'],
                u'最終原稿・組図': ['VISIBLE', 'WRITABLE']
            }
        }
        assert_equal(settings, expected)
