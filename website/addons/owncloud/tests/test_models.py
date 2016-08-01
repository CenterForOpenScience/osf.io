from nose.tools import *  # noqa
import mock

from tests.base import get_default_metaschema
from framework.auth.decorators import Auth

from website.addons.base.testing import models

from website.addons.owncloud.model import AddonOwnCloudNodeSettings
from website.addons.owncloud.tests.factories import (
    OwnCloudAccountFactory, OwnCloudNodeSettingsFactory,
    OwnCloudUserSettingsFactory
)
from website.addons.owncloud.tests import utils
from website.addons.owncloud.utils import ExternalAccountConverter

class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, utils.OwnCloudAddonTestCase):

    short_name='owncloud'
    ExternalAccountFactory = OwnCloudAccountFactory
    NodeSettingsFactory = OwnCloudNodeSettingsFactory
    NodeSettingsClass = AddonOwnCloudNodeSettings
    UserSettingsFactory = OwnCloudUserSettingsFactory


    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder': '/Documents',
            'owner': self.node,
            'node': self.node
        }

    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.set_node_settings(self.node_settings)

    def test_create_log(self):
        action = 'folder_selected'
        filename = 'pizza.nii'
        nlog = len(self.node.logs)
        self.node_settings.create_waterbutler_log(
            auth=Auth(user=self.user),
            action=action,
            metadata={'path': filename, 'materialized': filename},
        )
        self.node.reload()
        assert_equal(len(self.node.logs), nlog + 1)
        assert_equal(
            self.node.logs[-1].action,
            '{0}_{1}'.format(self.short_name, action),
        )
        assert_equal(
            self.node.logs[-1].params['filename'],
            filename
        )
    def test_set_folder(self):
        self.node_settings.set_folder('/', auth=Auth(self.user))
        # Folder was set
        assert_equal(self.node_settings.folder_name, '/')
        # Log was saved
        last_log = self.node.logs[-1]
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_serialize_credentials(self):
        credentials = self.node_settings.serialize_waterbutler_credentials()

        assert_is_not_none(self.node_settings.external_account.oauth_secret)
        expected = {'host': self.node_settings.external_account.oauth_key,
                'password': 'meoword',
                'username': 'catname'}

        assert_equal(credentials, expected)

    def test_serialize_settings(self):
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'folder': self.node_settings.folder_name,
        }
        assert_equal(settings, expected)

"""
class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, utils.OwnCloudAddonTestCase):

    ExternalAccountFactory = OwnCloudAccountFactory
"""
