from unittest import mock
import pytest
import unittest

from tests.base import get_default_metaschema

from framework.auth import Auth

from osf_tests.factories import DraftRegistrationFactory
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

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('addons.figshare.models.NodeSettings.archive_errors')
    def test_does_not_get_copied_to_registrations(self, mock_errors, mock_archive):
        registration = self.node.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.node.creator),
            draft_registration=DraftRegistrationFactory(branched_from=self.node)
        )
        assert not registration.has_addon('figshare')

    # Overrides

    @mock.patch('addons.figshare.client.FigshareClient.get_linked_folder_info')
    def test_set_folder(self, mock_info):
        # Differences from super: mocking, log action name
        folder_id = '1234567890'
        mock_info.return_value = dict(path='project', name='Folder', id='1234567890')
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        assert self.node_settings.folder_id == folder_id
        last_log = self.node.logs.latest()
        assert last_log.action == f'{self.short_name}_folder_selected'

    def test_serialize_settings(self):
        # Custom `expected`
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'container_id': self.node_settings.folder_id,
            'container_type': self.node_settings.folder_path
        }
        assert settings == expected


class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'figshare'
    full_name = 'figshare'
    ExternalAccountFactory = FigshareAccountFactory

    #TODO Test figshare options and figshare to_json
