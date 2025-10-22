# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest
import unittest

from addons.iqbrims.utils import get_folder_title
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
from osf.models import AbstractNode, RdmAddonOption
from osf_tests.factories import ProjectFactory, InstitutionFactory

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
                u'チェックリスト': [],
                u'スキャン結果': [],
                u'生データ': [],
                u'最終原稿・組図': []
            }
        }
        assert_equal(settings, expected)


class TestIQBRIMSNodeReceiver(unittest.TestCase):

    short_name = 'iqbrims'
    full_name = 'IQB-RIMS'
    folder_id = '1234567890'

    def setUp(self):
        super(TestIQBRIMSNodeReceiver, self).setUp()
        self.node = ProjectFactory()
        self.user_node = ProjectFactory()
        self.user = self.node.creator
        self.external_account = IQBRIMSAccountFactory()

        self.user.external_accounts.add(self.external_account)
        self.user.save()

        self.user_settings = self.user.add_addon(self.short_name)
        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
            metadata={'folder': self.folder_id}
        )
        self.user_settings.save()

        self.node_settings = IQBRIMSNodeSettingsFactory(
            external_account=self.external_account,
            user_settings=self.user_settings,
            folder_id=self.folder_id,
            owner=self.node
        )

        self.no_folders_node = ProjectFactory()
        self.no_folders_node.creator = self.user
        self.no_folders_node.save()
        self.user_settings.grant_oauth_access(
            node=self.no_folders_node,
            external_account=self.external_account,
            metadata={'folder': None}
        )
        self.no_folders_node_settings = IQBRIMSNodeSettingsFactory(
            external_account=self.external_account,
            user_settings=self.user_settings,
            folder_id=None,
            owner=self.no_folders_node
        )

        self.institution = InstitutionFactory()

    @mock.patch.object(NodeSettings, 'fetch_access_token')
    @mock.patch.object(IQBRIMSClient, 'rename_folder')
    @mock.patch.object(IQBRIMSClient, 'get_folder_info')
    def test_update_folder_name(self, mock_get_folder_info, mock_rename_folder, mock_fetch_access_token):
        mock_get_folder_info.return_value = {'title': 'dummy_folder_title'}
        mock_fetch_access_token.return_value = 'dummy_token'
        mock_rename_folder.return_value = None
        new_folder_title = get_folder_title(self.node)

        self.node.save(force_update=True)

        assert_equal(mock_get_folder_info.call_count, 1)
        assert_equal(mock_get_folder_info.call_args, ((), {'folder_id': self.folder_id}))

        assert_equal(mock_rename_folder.call_count, 1)
        assert_equal(mock_rename_folder.call_args[0], (self.folder_id, new_folder_title))

    @mock.patch.object(NodeSettings, 'fetch_access_token')
    @mock.patch.object(IQBRIMSClient, 'rename_folder')
    @mock.patch.object(IQBRIMSClient, 'get_folder_info')
    def test_update_folder_name_for_no_folders(self, mock_get_folder_info, mock_rename_folder, mock_fetch_access_token):
        mock_get_folder_info.return_value = {'title': 'dummy_folder_title'}
        mock_fetch_access_token.return_value = 'dummy_token'
        mock_rename_folder.return_value = None

        self.no_folders_node.save(force_update=True)

        assert_equal(mock_get_folder_info.call_count, 0)
        assert_equal(mock_rename_folder.call_count, 0)

    @mock.patch.object(IQBRIMSClient, 'rename_folder')
    def test_update_management_node_folder(self, mock_rename_folder):
        mock_rename_folder.return_value = None

        RdmAddonOption(
            provider=self.short_name,
            institution=self.institution,
            management_node=self.node
        ).save()

        self.node.save(force_update=True)

        assert_equal(mock_rename_folder.call_count, 0)

    @mock.patch.object(AbstractNode, 'find_by_institutions')
    def test_update_addon_state_for_iqbrims_option(self, mock_find_by_institutions):
        # IQB-RIMS calls add/delete_addon method when the RdmAddonOption is updated
        mock_find_by_institutions.return_value = [self.user_node]

        option = RdmAddonOption(
            provider=self.short_name,
            institution=self.institution,
            management_node=self.node,
            is_allowed=True,
        )
        with mock.patch.object(self.user_node, 'add_addon') as mock_add_addon:
            option.save()
            assert_equal(mock_add_addon.call_count, 1)

        with mock.patch.object(self.user_node, 'delete_addon') as mock_delete_addon:
            option.is_allowed = False
            option.save()
            assert_equal(mock_delete_addon.call_count, 1)

    @mock.patch.object(AbstractNode, 'find_by_institutions')
    def test_update_addon_state_for_other_option(self, mock_find_by_institutions):
        # IQB-RIMS ignores changes of RdmAddonOption of other add-ons
        mock_find_by_institutions.return_value = [self.user_node]

        option = RdmAddonOption(
            provider='some_other_addon',
            institution=self.institution,
            management_node=self.node,
            is_allowed=True,
        )
        with mock.patch.object(self.user_node, 'add_addon') as mock_add_addon:
            option.save()
            assert_equal(mock_add_addon.call_count, 0)

        with mock.patch.object(self.user_node, 'delete_addon') as mock_delete_addon:
            option.is_allowed = False
            option.save()
            assert_equal(mock_delete_addon.call_count, 0)
