# from nose.tools import *  # noqa
import unittest

import mock
import pytest
from nose.tools import (assert_false, assert_true,
                        assert_equal, assert_is_none)

from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin
)
from addons.onedrivebusiness import SHORT_NAME, FULL_NAME
from addons.onedrivebusiness import settings
from addons.onedrivebusiness.models import NodeSettings
from addons.onedrivebusiness.tests.factories import (
    OneDriveBusinessUserSettingsFactory,
    OneDriveBusinessNodeSettingsFactory,
    OneDriveBusinessAccountFactory
)
from framework.auth import Auth
from osf_tests.factories import ProjectFactory, DraftRegistrationFactory
from tests.base import get_default_metaschema

pytestmark = pytest.mark.django_db


class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = SHORT_NAME
    full_name = FULL_NAME
    ExternalAccountFactory = OneDriveBusinessAccountFactory


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = SHORT_NAME
    full_name = FULL_NAME
    ExternalAccountFactory = OneDriveBusinessAccountFactory
    NodeSettingsFactory = OneDriveBusinessNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = OneDriveBusinessUserSettingsFactory

    def test_registration_settings(self):
        registration = ProjectFactory()
        clone, message = self.node_settings.after_register(
            self.node, registration, self.user,
        )
        assert_is_none(clone)

    def test_before_register_no_settings(self):
        self.node_settings.user_settings = None
        message = self.node_settings.before_register(self.node, self.user)
        assert_false(message)

    def test_before_register_settings_and_auth(self):
        message = self.node_settings.before_register(self.node, self.user)
        assert_true(message)

    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.node.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.user),
            draft_registration=DraftRegistrationFactory(branched_from=self.node),
        )
        assert_false(registration.has_addon(SHORT_NAME))

    ## Overrides ##
    def test_has_auth(self):
        pass

    @mock.patch('addons.onedrivebusiness.models.NodeSettings.oauth_provider')
    @mock.patch('addons.onedrivebusiness.models.get_user_map')
    @mock.patch('addons.onedrivebusiness.models.OneDriveBusinessClient.folders')
    @mock.patch('addons.onedrivebusiness.models.OneDriveBusinessClient.create_folder')
    @mock.patch('addons.onedrivebusiness.models.OneDriveBusinessClient.get_permissions')
    def test_set_folder(self,
                        mock_onedrivebusinessclient_get_permissions,
                        mock_onedrivebusinessclient_create_folder,
                        mock_onedrivebusinessclient_folders, mock_get_user_map,
                        mock_node_settings_oauth_provider):
        self.node_settings.folder_id = None
        self.node_settings.user_settings = None

        assert_false(self.node_settings.complete)
        assert_false(self.node_settings.has_auth)
        external_account = mock.Mock()
        external_account.provider_id = 'user-11'
        external_account.oauth_key = 'key-11'
        external_account.oauth_secret = 'secret-15'
        mock_region = mock.Mock()
        mock_region.waterbutler_settings = {'root_folder_id': 'test-folder-1234'}
        mock_region_external_account = mock.Mock()
        mock_region_external_account.region = mock_region
        mock_region_external_account.external_account = external_account

        mock_oauth_provider = mock.Mock()
        mock_fetch_access_token = mock.Mock()
        mock_fetch_access_token.return_value = 'mock-access-token-1234'
        mock_oauth_provider.fetch_access_token = mock_fetch_access_token
        mock_node_settings_oauth_provider.return_value = mock_oauth_provider

        mock_onedrivebusinessclient_folders.return_value = []
        mock_onedrivebusinessclient_create_folder.return_value = {
            'id': 'mock-folder-1234',
        }
        mock_onedrivebusinessclient_get_permissions.return_value = {
            'value': [],
        }

        mock_get_user_map.return_value = {}

        self.node_settings.ensure_team_folder(mock_region_external_account)
        assert_true(self.node_settings.complete)
        assert_true(self.node_settings.has_auth)
        assert_equal(self.node_settings.folder_id, 'mock-folder-1234')
        assert_true('_GRDM_' in self.node_settings.folder_name)

    @mock.patch('addons.onedrivebusiness.models.get_region_external_account')
    @mock.patch('addons.onedrivebusiness.models.NodeSettings.oauth_provider')
    def test_serialize_credentials(self, mock_node_settings_oauth_provider,
                                   mock_get_region_external_account):
        external_account = mock.Mock()
        external_account.provider_id = 'user-11'
        external_account.oauth_key = 'key-11'
        external_account.oauth_secret = 'secret-15'
        mock_region_external_account = mock.Mock()
        mock_region_external_account.external_account = external_account
        mock_get_region_external_account.return_value = mock_region_external_account
        mock_oauth_provider = mock.Mock()
        mock_fetch_access_token = mock.Mock()
        mock_fetch_access_token.return_value = 'mock-access-token-1234'
        mock_oauth_provider.fetch_access_token = mock_fetch_access_token
        mock_node_settings_oauth_provider.return_value = mock_oauth_provider

        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'token': 'mock-access-token-1234'}
        assert_equal(credentials, expected)

    def test_serialize_settings(self):
        self.node_settings.drive_id = 'drive-1234'
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'drive': 'drive-1234', 'folder': self.node_settings.folder_id}
        assert_equal(settings, expected)
