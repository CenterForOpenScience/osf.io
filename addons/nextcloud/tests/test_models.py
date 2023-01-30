from nose.tools import assert_is_not_none, assert_equal
import pytest
import unittest

from unittest import mock
from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)

from addons.nextcloud.models import NodeSettings
from osf_tests.test_archiver import MockAddon
from addons.nextcloud.tests.factories import (
    NextcloudAccountFactory, NextcloudNodeSettingsFactory,
    NextcloudUserSettingsFactory, NextcloudFileFactory
)
from addons.nextcloud.settings import USE_SSL
from admin.rdm_addons.utils import get_rdm_addon_option
from osf_tests.factories import (
    ExternalAccountFactory,
    UserFactory, InstitutionFactory
)

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'nextcloud'
    full_name = 'Nextcloud'
    UserSettingsFactory = NextcloudUserSettingsFactory
    ExternalAccountFactory = NextcloudAccountFactory


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'nextcloud'
    full_name = 'Nextcloud'
    ExternalAccountFactory = NextcloudAccountFactory
    NodeSettingsFactory = NextcloudNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = NextcloudUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder_id': '/Documents',
            'owner': self.node
        }

    def test_serialize_credentials(self):
        credentials = self.node_settings.serialize_waterbutler_credentials()

        assert_is_not_none(self.node_settings.external_account.oauth_secret)
        expected = {
            'host': self.node_settings.external_account.oauth_secret,
            'password': 'meoword',
            'username': 'catname'
        }

        assert_equal(credentials, expected)

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'folder': self.node_settings.folder_id,
            'verify_ssl': USE_SSL
        }
        assert_equal(settings, expected)


class TestNextcloudFile(unittest.TestCase):
    def setUp(self):
        super(TestNextcloudFile, self).setUp()

    def test_get_hash_for_timestamp_return_none(self):
        test_obj = NextcloudFileFactory()
        res = test_obj.get_hash_for_timestamp()
        assert res == (None, None)

    def test_my_node_settings(self):
        with mock.patch('osf.models.mixins.AddonModelMixin.get_addon') as mock_get_addon:
            test_obj = NextcloudFileFactory()
            mock_addon = MockAddon()
            mock_get_addon.return_value = mock_addon
            res = test_obj._my_node_settings()
            assert res != None

    def test_my_node_settings_return_none(self):
        test_obj = NextcloudFileFactory()
        res = test_obj._my_node_settings()
        assert res == None

    def test_get_timestamp(self):
        mock_utils = mock.MagicMock()
        mock_utils.return_value = 'abc'
        with mock.patch('osf.models.mixins.AddonModelMixin.get_addon') as mock_get_addon:
            with mock.patch('addons.nextcloudinstitutions.utils.get_timestamp', mock_utils):
                test_obj = NextcloudFileFactory()
                mock_addon = MockAddon()
                mock_get_addon.return_value = mock_addon
                res = test_obj.get_timestamp()
                assert res == 'abc'

    def test_get_timestamp_return_none(self):
        test_obj = NextcloudFileFactory()
        res = test_obj.get_timestamp()
        assert res == (None, None, None)

    def test_set_timestamp(self):
        mock_utils = mock.MagicMock()
        mock_utils.return_value = 'abc'
        with mock.patch('osf.models.mixins.AddonModelMixin.get_addon') as mock_get_addon:
            with mock.patch('addons.nextcloudinstitutions.utils.set_timestamp', mock_utils):
                test_obj = NextcloudFileFactory()
                mock_addon = MockAddon()
                mock_get_addon.return_value = mock_addon
                test_obj.set_timestamp('timestamp_data', 'timestamp_status', 'context')

    def test_get_hash_for_timestamp(self):
        mock_hash = mock.MagicMock()
        mock_hash = {'sha512': 'data_sha512'}
        with mock.patch('osf.models.mixins.AddonModelMixin.get_addon') as mock_get_addon:
            with mock.patch('addons.nextcloud.models.NextcloudFile._hashes', mock_hash):
                test_obj = NextcloudFileFactory()
                mock_addon = MockAddon()
                mock_get_addon.return_value = mock_addon
                res = test_obj.get_hash_for_timestamp()
                assert res == ('sha512', 'data_sha512')
