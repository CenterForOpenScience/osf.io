from nose.tools import *
import mock

from tests.factories import AuthUserFactory
from framework.auth.decorators import Auth
from website.addons.dataverse.model import AddonDataverseUserSettings, \
    AddonDataverseNodeSettings, DataverseFile
from website.addons.dataverse.tests.utils import create_mock_connection, \
    DataverseAddonTestCase


class TestCallbacks(DataverseAddonTestCase):

    def test_dataverse_file_url(self):

        # Create some dataverse file
        dvf = DataverseFile()
        dvf.file_id = '12345'
        dvf.save()

        # Assert url is correct
        assert_equal('dataverse/file/12345', dvf.file_url)

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


class TestDataverseNodeSettings(DataverseAddonTestCase):

    def test_deauthorize(self):

        self.node_settings.deauthorize()

        assert_false(self.node_settings.dataverse_username)
        assert_false(self.node_settings.dataverse_password)
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user)

    @mock.patch('website.addons.dataverse.model.connect')
    def test_to_json(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        json = self.node_settings.to_json(self.user)

        assert_true(json['authorized'])
        assert_true(json['connected'])
        assert_true(json['user_dataverse_connected'])

        # TODO: Check authorized user name/url (requires refactor)
        assert_equal(self.user_settings.dataverse_username,
                     json['authorized_dataverse_user'])
        assert_equal(self.node_settings.dataverse, json['dataverse'])
        assert_equal(self.node_settings.dataverse_alias, json['dataverse_alias'])
        assert_equal(self.node_settings.study_hdl, json['study_hdl'])
        assert_equal(3, len(json['dataverses']))
        assert_equal(3, len(json['study_names']))

        assert_true(json['dataverse_url'])
        assert_true(json['dataverse_url'])


    @mock.patch('website.addons.dataverse.model.connect')
    def test_to_json_unauthorized(self, mock_connection):
        mock_connection.return_value = create_mock_connection()

        user2 = AuthUserFactory()
        user2.add_addon('dataverse', override=True)
        user2_settings = user2.get_addon('dataverse')
        user2_settings.dataverse_username = 'Different'
        user2_settings.save()

        json = self.node_settings.to_json(user2)

        assert_false(json['authorized'])
        assert_true(json['connected'])
        assert_true(json['user_dataverse_connected'])

        assert_equal(self.user_settings.dataverse_username,
                     json['authorized_dataverse_user'])
        assert_equal(self.node_settings.dataverse, json['dataverse'])
        assert_equal(self.node_settings.study_hdl, json['study_hdl'])
        assert_equal(3, len(json['dataverses']))
        assert_equal(3, len(json['study_names']))

        assert_true(json['dataverse_url'])
        assert_true(json['dataverse_url'])

    @mock.patch('website.addons.dataverse.model.connect')
    def test_to_json_bad_connection(self, mock_connection):
        mock_connection.return_value = None

        json = self.node_settings.to_json(self.user)

        assert_true(json['authorized'])
        assert_false(json['connected'])
        assert_false(json['user_dataverse_connected'])

    @mock.patch('website.addons.dataverse.model.connect')
    @mock.patch('website.addons.dataverse.model.get_study')
    def test_to_json_no_study(self, mock_study, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_study.return_value = None

        json = self.node_settings.to_json(self.user)

        assert_true(json['authorized'])
        assert_true(json['connected'])
        assert_true(json['user_dataverse_connected'])

        assert_equal(self.user_settings.dataverse_username,
                     json['authorized_dataverse_user'])
        assert_equal(self.node_settings.dataverse, json['dataverse'])
        assert_equal(self.node_settings.dataverse_alias, json['dataverse_alias'])
        assert_equal(None, json['study_hdl'])
        assert_equal(3, len(json['dataverses']))
        assert_equal(3, len(json['study_names']))

        assert_not_in('dataverse_url', json)
        assert_not_in('study_url', json)

