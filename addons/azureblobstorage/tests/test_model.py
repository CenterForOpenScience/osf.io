from nose.tools import *  # noqa
import mock
import pytest
import unittest

from tests.base import get_default_metaschema
from tests.factories import ProjectFactory

from framework.auth import Auth
from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin
)
from addons.azureblobstorage.models import NodeSettings
from addons.azureblobstorage.tests.factories import (
    AzureBlobStorageUserSettingsFactory,
    AzureBlobStorageNodeSettingsFactory,
    AzureBlobStorageAccountFactory
)

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'azureblobstorage'
    full_name = 'Azure Blob Storage'
    ExternalAccountFactory = AzureBlobStorageAccountFactory

class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'azureblobstorage'
    full_name = 'Azure Blob Storage'
    ExternalAccountFactory = AzureBlobStorageAccountFactory
    NodeSettingsFactory = AzureBlobStorageNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = AzureBlobStorageUserSettingsFactory

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

    def test_before_register_no_auth(self):
        self.node_settings.external_account = None
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
            data='hodor',
        )
        assert_false(registration.has_addon('azureblobstorage'))

    ## Overrides ##

    def test_serialize_credentials(self):
        self.user_settings.external_accounts[0].oauth_key = 'key-11'
        self.user_settings.external_accounts[0].oauth_secret = 'secret-15'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'account_name': self.node_settings.external_account.oauth_key,
                    'account_key': self.node_settings.external_account.oauth_secret}
        assert_equal(credentials, expected)


    @mock.patch('addons.azureblobstorage.models.container_exists')
    def test_set_folder(self, mock_exists):
        mock_exists.return_value = True
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Container was set
        assert_equal(self.node_settings.folder_id, folder_id)
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_bucket_linked'.format(self.short_name))

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'container': self.node_settings.folder_id}
        assert_equal(settings, expected)
