import mock
from nose.tools import *  # noqa
import pytest
import unittest

from tests.base import get_default_metaschema
from osf_tests.factories import ProjectFactory

from framework.auth import Auth
from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin
)
from addons.weko.models import NodeSettings
from addons.weko.tests.factories import (
    WEKOUserSettingsFactory,
    WEKONodeSettingsFactory,
    WEKOAccountFactory
)
from addons.weko import client

pytestmark = pytest.mark.django_db

class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'weko'
    full_name = 'WEKO'
    ExternalAccountFactory = WEKOAccountFactory

class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'weko'
    full_name = 'WEKO'
    ExternalAccountFactory = WEKOAccountFactory
    NodeSettingsFactory = WEKONodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = WEKOUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'index_id': '1234567890',
            'owner': self.node
        }

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
        assert_false(registration.has_addon('weko'))

    ## Overrides ##

    def test_serialize_credentials(self):
        self.user_settings.external_accounts[0].oauth_key = 'key-17'
        self.user_settings.save()
        credentials = self.node_settings.serialize_waterbutler_credentials()

        expected = {'token': self.node_settings.external_account.oauth_key,
                    'user_id': self.node_settings.external_account.provider_id.split(':')[1]}
        assert_equal(credentials, expected)

    def test_create_log(self):
        action = 'file_added'
        path = 'pizza.nii'
        nlog = self.node.logs.count()
        self.node_settings.create_waterbutler_log(
            auth=Auth(user=self.user),
            action=action,
            metadata={'path': path, 'materialized': path},
        )
        self.node.reload()
        assert_equal(self.node.logs.count(), nlog + 1)
        assert_equal(
            self.node.logs.latest().action,
            '{0}_{1}'.format(self.short_name, action),
        )
        assert_equal(
            self.node.logs.latest().params['filename'],
            path
        )

    def test_set_folder(self):
        index_id = '1234567890'
        self.node_settings.set_folder(client.Index(index_id=index_id,
                                                   title='Test'),
                                      auth=Auth(self.user))
        self.node_settings.save()
        # Container was set
        assert_equal(self.node_settings.index_id, index_id)
        # Log was saved
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_index_linked'.format(self.short_name))

    def test_serialize_settings(self):
        pass
