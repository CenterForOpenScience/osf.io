from nose.tools import *
import mock

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory
from website.addons.dataverse.model import AddonDataverseUserSettings, \
    AddonDataverseNodeSettings

from utils import create_mock_connection, DataverseAddonTestCase


class TestCallbacks(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.model.connect')
    def test_user_settings(self, mock_connection):

        # Create user settings
        dataverse = AddonDataverseUserSettings()
        creator = self.project.creator

        # Dataverse is not authorized by default
        mock_connection.return_value = create_mock_connection('wrong', 'info')
        assert_false(dataverse.to_json(creator)['authorized'])
        assert_false(dataverse.to_json(creator)['authorized_dataverse_user'])

        # With valid credentials, dataverse is authorized
        mock_connection.return_value = create_mock_connection()
        dataverse.dataverse_username = 'snowman'
        assert_true(dataverse.to_json(creator)['authorized'])
        assert_equals(dataverse.to_json(creator)['authorized_dataverse_user'],
                      'snowman')

    def test_deauthorize(self):

        self.node_settings.deauthorize()

        assert_false(self.node_settings.dataverse_username)
        assert_false(self.node_settings.dataverse_password)
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user)

