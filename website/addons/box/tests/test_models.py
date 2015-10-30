# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa (PEP8 asserts)

from tests.base import OsfTestCase

from website.addons.box.tests.factories import (
    BoxUserSettingsFactory,
    BoxNodeSettingsFactory,
    BoxAccountFactory
)
from website.addons.box.model import BoxNodeSettings

from website.addons.base.testing import models


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'box'
    full_name = 'Box'
    ExternalAccountFactory = BoxAccountFactory

    NodeSettingsFactory = BoxNodeSettingsFactory
    NodeSettingsClass = BoxNodeSettings
    UserSettingsFactory = BoxUserSettingsFactory

    def setUp(self):
        self.mock_update_data = mock.patch.object(
            BoxNodeSettings,
            '_update_folder_data'
        )
        self.mock_update_data.start()
        super(TestNodeSettings, self).setUp()

    def tearDown(self):
        self.mock_update_data.stop()
        super(TestNodeSettings, self).tearDown()


    def test_complete_false(self):
        self.user_settings.oauth_grants[self.node._id].pop(self.external_account._id)

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_fields(self):
        node_settings = BoxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'folder_id'))
        assert_true(hasattr(node_settings, 'user_settings'))

    def test_folder_defaults_to_none(self):
        node_settings = BoxNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.folder_id)

    def test_has_auth(self):
        self.user.external_accounts = []
        self.user_settings.reload()
        settings = BoxNodeSettings(user_settings=self.user_settings)
        settings.save()
        assert_false(settings.has_auth)

        self.user.external_accounts.append(self.external_account)
        settings.reload()
        assert_true(settings.has_auth)

    def test_clear_auth(self):
        node_settings = BoxNodeSettingsFactory()
        node_settings.external_account = BoxAccountFactory()
        node_settings.user_settings = BoxUserSettingsFactory()
        node_settings.save()

        node_settings.clear_auth()

        assert_is_none(node_settings.external_account)
        assert_is_none(node_settings.folder_id)
        assert_is_none(node_settings.user_settings)

    def test_to_json(self):
        settings = self.node_settings
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], 'box')

    def test_delete(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        old_logs = self.node.logs
        self.node_settings.delete()
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)
        assert_true(self.node_settings.deleted)
        assert_equal(self.node.logs, old_logs)

    def test_deauthorize(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)

        last_log = self.node.logs[-1]
        assert_equal(last_log.action, 'box_node_deauthorized')
        params = last_log.params
        assert_in('node', params)
        assert_in('project', params)
        assert_in('folder_id', params)

    @mock.patch("website.addons.box.model.BoxNodeSettings._update_folder_data")
    def test_set_folder(self, mock_update_folder):
        folder_id = '1234567890'
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        # Folder was set
        assert_equal(self.node_settings.folder_id, folder_id)
        # Log was saved
        last_log = self.node.logs[-1]
        assert_equal(last_log.action, 'box_folder_selected')

    def test_set_user_auth(self):
        node_settings = BoxNodeSettingsFactory()
        user_settings = BoxUserSettingsFactory()
        external_account = BoxAccountFactory()

        user_settings.owner.external_accounts.append(external_account)
        user_settings.save()

        node_settings.external_account = external_account
        node_settings.set_user_auth(user_settings)
        node_settings.save()

        assert_true(node_settings.has_auth)
        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs[-1]
        assert_equal(last_log.action, 'box_node_authorized')
        log_params = last_log.params
        assert_equal(log_params['folder_id'], node_settings.folder_id)
        assert_equal(log_params['node'], node_settings.owner._primary_key)
        assert_equal(last_log.user, user_settings.owner)

    @mock.patch("website.addons.box.model.refresh_oauth_key")
    def test_serialize_credentials(self, mock_refresh):
        mock_refresh.return_value = True
        super(TestNodeSettings, self).test_serialize_credentials()

class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'box'
    full_name = 'Box'
    ExternalAccountFactory = BoxAccountFactory
