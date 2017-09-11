import mock
from nose.tools import assert_false, assert_equal
import pytest
import unittest

from osf_tests.utils import mock_archive

from framework.auth import Auth

from addons.figshare.tests.factories import (
    FigshareUserSettingsFactory,
    FigshareNodeSettingsFactory,
    FigshareAccountFactory
)
from addons.figshare.models import NodeSettings

from addons.base.tests import models

pytestmark = pytest.mark.django_db


class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'figshare'
    full_name = 'figshare'

    ExternalAccountFactory = FigshareAccountFactory
    NodeSettingsFactory = FigshareNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = FigshareUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder_id': '1234567890',
            'folder_path': 'fileset',
            'folder_name': 'Camera Uploads',
            'owner': self.node
        }

    @mock.patch('addons.figshare.models.NodeSettings.archive_errors')
    def test_does_not_get_copied_to_registrations(self, mock_errors):
        with mock_archive(self.node, data='hodor', autoapprove=True) as registration:
            assert_true(registration.title)
            assert_false(registration.has_addon('figshare'))

    # Overrides

    @mock.patch('addons.figshare.client.FigshareClient.get_linked_folder_info')
    def test_set_folder(self, mock_info):
        # Differences from super: mocking, log action name
        folder_id = '1234567890'
        mock_info.return_value = dict(path='project', name='Folder', id='1234567890')
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        assert_equal(self.node_settings.folder_id, folder_id)
        last_log = self.node.logs.latest()
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_serialize_settings(self):
        # Custom `expected`
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'container_id': self.node_settings.folder_id,
            'container_type': self.node_settings.folder_path
        }
        assert_equal(settings, expected)


class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'figshare'
    full_name = 'figshare'
    ExternalAccountFactory = FigshareAccountFactory

    #TODO Test figshare options and figshare to_json
