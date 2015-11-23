# -*- coding: utf-8 -*-
import mock

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from website.addons.onedrive.model import (
    OneDriveUserSettings, OneDriveNodeSettings
)
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.onedrive.tests.factories import (
    OneDriveUserSettingsFactory, OneDriveNodeSettingsFactory,
)
from website.addons.base import exceptions


class TestUserSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestUserSettingsModel, self).setUp()
        self.user = UserFactory()

#      def test_has_auth(self):
#          user_settings = OneDriveUserSettingsFactory(access_token=None)
#          assert_false(user_settings.has_auth)
#          user_settings.access_token = '12345'
#          user_settings.save()
#          assert_true(user_settings.has_auth)
#
    def test_delete(self):
        user_settings = OneDriveUserSettingsFactory()
        user_settings.access_token = "122"
        user_settings.delete()
        user_settings.save()
        assert_true(user_settings.deleted)

class TestOneDriveNodeSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestOneDriveNodeSettingsModel, self).setUp()
        self.user = UserFactory()
        self.user.add_addon('onedrive')
        self.user.save()
        self.user_settings = self.user.get_addon('onedrive')
        self.project = ProjectFactory()
        self.node_settings = OneDriveNodeSettingsFactory(
            user_settings=self.user_settings,
            owner=self.project
        )

    def test_folder_defaults_to_none(self):
        node_settings = OneDriveNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.folder_id)

    def test_to_json(self):
        settings = self.node_settings
        user = UserFactory()
        result = settings.to_json(user)
        assert_equal(result['addon_short_name'], 'onedrive')

    def test_delete(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        old_logs = self.project.logs
        self.node_settings.delete()
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)
        assert_true(self.node_settings.deleted)


    def test_deauthorize(self):
        assert_true(self.node_settings.user_settings)
        assert_true(self.node_settings.folder_id)
        self.node_settings.deauthorize(auth=Auth(self.user))
        self.node_settings.save()
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder_id, None)

        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'onedrive_node_deauthorized')
        params = last_log.params
        assert_in('node', params)
        assert_in('project', params)
        assert_in('folder', params)

    def test_set_user_auth(self):
        node_settings = OneDriveNodeSettingsFactory()
        user_settings = OneDriveUserSettingsFactory()

        node_settings.set_user_auth(user_settings)
        node_settings.save()

        assert_equal(node_settings.user_settings, user_settings)
        # A log was saved
        last_log = node_settings.owner.logs[-1]
        assert_equal(last_log.action, 'onedrive_node_authorized')

    def test_serialize_credentials_not_authorized(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        with assert_raises(exceptions.AddonError):
            self.node_settings.serialize_waterbutler_credentials()

