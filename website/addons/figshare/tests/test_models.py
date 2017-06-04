import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase, get_default_metaschema
from tests.factories import ProjectFactory, AuthUserFactory

from framework.auth import Auth
from website.addons.figshare import settings as figshare_settings

from website.addons.figshare.tests.factories import (
    FigshareUserSettingsFactory,
    FigshareNodeSettingsFactory,
    FigshareAccountFactory
)
from website.addons.figshare.model import FigshareNodeSettings

from website.addons.base.testing import models

class TestNodeSettings(models.OAuthAddonNodeSettingsTestSuiteMixin, OsfTestCase):

    short_name = 'figshare'
    full_name = 'figshare'

    ExternalAccountFactory = FigshareAccountFactory
    NodeSettingsFactory = FigshareNodeSettingsFactory
    NodeSettingsClass = FigshareNodeSettings
    UserSettingsFactory = FigshareUserSettingsFactory

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder_id': '1234567890',
            'folder_path': 'fileset',
            'owner': self.node
        }

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('website.addons.figshare.model.FigshareNodeSettings.archive_errors')
    def test_does_not_get_copied_to_registrations(self, mock_errors, mock_archive):
        registration = self.node.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.node.creator),
            data='hodor'
        )
        assert_false(registration.has_addon('figshare'))

    # Overrides

    @mock.patch('website.addons.figshare.client.FigshareClient.get_linked_folder_info')
    def test_set_folder(self, mock_info):
        # Differences from super: mocking, log action name
        folder_id = '1234567890'
        mock_info.return_value=dict(path='project', name='Folder', id='1234567890')
        self.node_settings.set_folder(folder_id, auth=Auth(self.user))
        self.node_settings.save()
        assert_equal(self.node_settings.folder_id, folder_id)
        last_log = self.node.logs[-1]
        assert_equal(last_log.action, '{0}_folder_selected'.format(self.short_name))

    def test_serialize_settings(self):
        # Custom `expected`
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {
            'container_id': self.node_settings.folder_id,
            'container_type': self.node_settings.folder_path
        }
        assert_equal(settings, expected)



class TestUserSettings(models.OAuthAddonUserSettingTestSuiteMixin, OsfTestCase):

    short_name = 'figshare'
    full_name = 'figshare'
    ExternalAccountFactory = FigshareAccountFactory

    #TODO Test figshare options and figshare to_json
