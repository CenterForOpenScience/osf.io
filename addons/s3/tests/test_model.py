# from nose.tools import *  # noqa
import mock
from nose.tools import (assert_false, assert_true,
    assert_equal, assert_is_none)
import pytest
import unittest

from framework.auth import Auth

from osf_tests.factories import ProjectFactory
from tests.base import get_default_metaschema

from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin
)
from addons.s3.models import NodeSettings
from addons.s3.tests.factories import (
    S3UserSettingsFactory,
    S3NodeSettingsFactory,
    S3AccountFactory
)

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 's3'
    full_name = 'Amazon S3'
    ExternalAccountFactory = S3AccountFactory

class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 's3'
    full_name = 'Amazon S3'
    ExternalAccountFactory = S3AccountFactory
    NodeSettingsFactory = S3NodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = S3UserSettingsFactory

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
        assert_false(registration.has_addon('s3'))

    ## Overrides ##

    def test_serialize_credentials(self):
        self.user_settings.external_accounts[0].oauth_key = 'key-11'
        self.user_settings.external_accounts[0].oauth_secret = 'secret-15'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'access_key': self.node_settings.external_account.oauth_key,
                    'secret_key': self.node_settings.external_account.oauth_secret}
        assert_equal(credentials, expected)

    @mock.patch('addons.s3.models.bucket_exists')
    @mock.patch('addons.s3.models.get_bucket_location_or_error')
    def test_set_folder(self, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = ''
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Bucket was set
        assert_equal(self.node_settings.folder_id, folder_id)
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_bucket_linked'.format(self.short_name))

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'bucket': self.node_settings.folder_id,
                    'encrypt_uploads': self.node_settings.encrypt_uploads}
        assert_equal(settings, expected)
