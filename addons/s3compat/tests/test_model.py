# from nose.tools import *  # noqa
import mock
from nose.tools import (assert_false, assert_true,
    assert_equal, assert_is_none)
import pytest
import unittest

from framework.auth import Auth

from osf_tests.factories import ProjectFactory, DraftRegistrationFactory
from tests.base import get_default_metaschema

from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin
)
from addons.s3compat.models import NodeSettings
from addons.s3compat.tests.factories import (
    S3CompatUserSettingsFactory,
    S3CompatNodeSettingsFactory,
    S3CompatAccountFactory
)

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 's3compat'
    full_name = 'S3 Compatible Storage'
    ExternalAccountFactory = S3CompatAccountFactory

class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 's3compat'
    full_name = 'S3 Compatible Storage'
    ExternalAccountFactory = S3CompatAccountFactory
    NodeSettingsFactory = S3CompatNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = S3CompatUserSettingsFactory

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
            draft_registration=DraftRegistrationFactory(branched_from=self.node),
        )
        assert_false(registration.has_addon('s3compat'))

    ## Overrides ##

    def test_serialize_credentials(self):
        self.user_settings.external_accounts[0].provider_id = 'host-11\tuser-11'
        self.user_settings.external_accounts[0].oauth_key = 'key-11'
        self.user_settings.external_accounts[0].oauth_secret = 'secret-15'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'host': self.node_settings.external_account.provider_id.split('\t')[0],
                    'access_key': self.node_settings.external_account.oauth_key,
                    'secret_key': self.node_settings.external_account.oauth_secret}
        assert_equal(credentials, expected)

    @mock.patch('addons.s3compat.models.bucket_exists')
    @mock.patch('addons.s3compat.models.get_bucket_location_or_error')
    @mock.patch('addons.s3compat.models.find_service_by_host')
    def test_serialize_credentials_undefined_location(self, mock_service, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = 'dummy-1'
        mock_service.return_value = {'name': 'Dummy', 'host': 'dummy.example.com'}
        self.user_settings.external_accounts[0].provider_id = 'host-11\tuser-11'
        self.user_settings.external_accounts[0].oauth_key = 'key-11'
        self.user_settings.external_accounts[0].oauth_secret = 'secret-15'
        self.user_settings.save()
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'host': self.node_settings.external_account.provider_id.split('\t')[0],
                    'access_key': self.node_settings.external_account.oauth_key,
                    'secret_key': self.node_settings.external_account.oauth_secret}
        assert_equal(credentials, expected)

    @mock.patch('addons.s3compat.models.bucket_exists')
    @mock.patch('addons.s3compat.models.get_bucket_location_or_error')
    @mock.patch('addons.s3compat.models.find_service_by_host')
    def test_serialize_credentials_defined_location(self, mock_service, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = 'dummy-2'
        mock_service.return_value = {'name': 'Dummy',
                                     'host': 'dummy.example.com',
                                     'bucketLocations': {'dummy-1': {'name': 'Location1'},
                                                         'dummy-2': {'name': 'Location2',
                                                                     'host': 'host-location2'}}}
        self.user_settings.external_accounts[0].provider_id = 'host-11\tuser-11'
        self.user_settings.external_accounts[0].oauth_key = 'key-11'
        self.user_settings.external_accounts[0].oauth_secret = 'secret-15'
        self.user_settings.save()
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'host': 'host-location2',
                    'access_key': self.node_settings.external_account.oauth_key,
                    'secret_key': self.node_settings.external_account.oauth_secret}
        assert_equal(credentials, expected)

        mock_location.return_value = 'dummy-1'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'host': self.node_settings.external_account.provider_id.split('\t')[0],
                    'access_key': self.node_settings.external_account.oauth_key,
                    'secret_key': self.node_settings.external_account.oauth_secret}
        assert_equal(credentials, expected)

    @mock.patch('addons.s3compat.models.bucket_exists')
    @mock.patch('addons.s3compat.models.get_bucket_location_or_error')
    @mock.patch('addons.s3compat.models.find_service_by_host')
    def test_set_folder(self, mock_service, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = ''
        mock_service.return_value = {'name': 'Dummy', 'host': 'dummy.example.com'}
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Bucket was set
        assert_equal(self.node_settings.folder_id, folder_id)
        assert_equal(self.node_settings.folder_name, '{} (Default)'.format(folder_id))
        assert_equal(self.node_settings.folder_location, '')
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_bucket_linked'.format(self.short_name))

    @mock.patch('addons.s3compat.models.bucket_exists')
    @mock.patch('addons.s3compat.models.get_bucket_location_or_error')
    @mock.patch('addons.s3compat.models.find_service_by_host')
    def test_set_folder_undefined_location(self, mock_service, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = 'dummy-1'
        mock_service.return_value = {'name': 'Dummy', 'host': 'dummy.example.com'}
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Bucket was set
        assert_equal(self.node_settings.folder_id, folder_id)
        assert_equal(self.node_settings.folder_name, '{} (dummy-1)'.format(folder_id))
        assert_equal(self.node_settings.folder_location, 'dummy-1')
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_bucket_linked'.format(self.short_name))

    @mock.patch('addons.s3compat.models.bucket_exists')
    @mock.patch('addons.s3compat.models.get_bucket_location_or_error')
    @mock.patch('addons.s3compat.models.find_service_by_host')
    def test_set_folder_defined_location(self, mock_service, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = 'dummy-2'
        mock_service.return_value = {'name': 'Dummy',
                                     'host': 'dummy.example.com',
                                     'bucketLocations': {'dummy-1': {'name': 'Location1'},
                                                         'dummy-2': {'name': 'Location2'}}}
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Bucket was set
        assert_equal(self.node_settings.folder_id, folder_id)
        assert_equal(self.node_settings.folder_name, '{} (Location2)'.format(folder_id))
        assert_equal(self.node_settings.folder_location, 'dummy-2')
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_bucket_linked'.format(self.short_name))

    @mock.patch('addons.s3compat.models.bucket_exists')
    @mock.patch('addons.s3compat.models.get_bucket_location_or_error')
    @mock.patch('addons.s3compat.models.find_service_by_host')
    def test_set_folder_change_encrypt_uploads_with_encryption_setting(self, mock_service, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = 'dummy-3'
        mock_service.return_value = {'name': 'Dummy',
                                     'host': 'dummy.example.com',
                                     'serverSideEncryption': False}
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # encrypt_uploads set
        assert_equal(self.node_settings.encrypt_uploads, False)

        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_bucket_linked'.format(self.short_name))

    @mock.patch('addons.s3compat.models.bucket_exists')
    @mock.patch('addons.s3compat.models.get_bucket_location_or_error')
    @mock.patch('addons.s3compat.models.find_service_by_host')
    def test_set_folder_change_encrypt_uploads_with_no_encryption_setting(self, mock_service, mock_location, mock_exists):
        mock_exists.return_value = True
        mock_location.return_value = 'dummy-3'
        mock_service.return_value = {'name': 'Dummy',
                                     'host': 'dummy.example.com',}
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # encrypt_uploads set
        assert_equal(self.node_settings.encrypt_uploads, True)

        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_bucket_linked'.format(self.short_name))

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'bucket': self.node_settings.folder_id,
                    'encrypt_uploads': self.node_settings.encrypt_uploads}
        assert_equal(settings, expected)
