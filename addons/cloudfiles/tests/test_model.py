# -*- coding: utf-8 -*-
# from nose.tools import *  # noqa
import mock

import pytest
import unittest

from nose.tools import (assert_false, assert_true,
    assert_equal, assert_is_none)

from framework.auth import Auth

from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin
)
from addons.cloudfiles.models import NodeSettings
from addons.cloudfiles.tests.factories import (
    CloudFilesUserSettingsFactory,
    CloudFilesNodeSettingsFactory,
    CloudFilesAccountFactory
)

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    short_name = 'cloudfiles'
    full_name = 'Cloud Files'
    ExternalAccountFactory = CloudFilesAccountFactory

class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):
    short_name = 'cloudfiles'
    full_name = 'Cloud Files'
    ExternalAccountFactory = CloudFilesAccountFactory
    NodeSettingsFactory = CloudFilesNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = CloudFilesUserSettingsFactory

    ## Overrides ##
    def test_serialize_credentials(self):
        self.node_settings.folder_region = 'Narnia'
        self.node_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()
        expected = {'username': self.user_settings.external_accounts[0].provider_id,
                    'token': 'some-super-secret',
                    'region': 'Narnia'}
        assert_equal(credentials, expected)

    def test_set_folder(self):
        folder_id = 'special chars are √'
        region = 'FAK'
        self.node_settings.set_folder(folder_id, region, auth=Auth(self.user))
        self.node_settings.save()
        # Bucket was set
        assert_equal(self.node_settings.folder_id, folder_id)
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_container_linked'.format(self.short_name))


    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'container': self.node_settings.folder_id}
        assert_equal(settings, expected)
