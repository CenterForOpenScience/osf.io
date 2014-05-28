from nose.tools import *
import mock

from tests.factories import AuthUserFactory
from tests.factories import UserFactory, ProjectFactory
from framework.auth.decorators import Auth
from website.addons.dataverse.model import AddonDataverseUserSettings, \
    AddonDataverseNodeSettings, DataverseFile
from website.addons.dataverse.tests.utils import create_mock_connection, \
    create_mock_dataverse, DataverseAddonTestCase


class TestDataverseFile(DataverseAddonTestCase):

    def test_dataverse_file_url(self):

        # Create some dataverse file
        dvf = DataverseFile()
        dvf.file_id = '12345'
        dvf.save()

        # Assert url is correct
        assert_equal('dataverse/file/12345', dvf.file_url)


class TestDataverseUserSettings(DataverseAddonTestCase):

    @mock.patch('website.addons.dataverse.model.connect')
    def test_fields(self, mock_connection):

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

    def test_clear(self):

        self.user_settings.clear()

        # Fields were cleared, but settings were not deleted
        assert_false(self.user_settings.dataverse_username)
        assert_false(self.user_settings.dataverse_password)
        assert_false(self.user_settings.deleted)

        # Authorized node settings were deauthorized
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user_settings)

        # Authorized node settings were not deleted
        assert_false(self.node_settings.deleted)

    def test_clear_and_delete(self):

        self.user_settings.clear(delete=True)

        # Fields were cleared, but settings were not deleted
        assert_false(self.user_settings.dataverse_username)
        assert_false(self.user_settings.dataverse_password)
        assert_false(self.user_settings.deleted)

        # Authorized node settings were deauthorized
        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user_settings)

        # Authorized node settings were deleted
        assert_true(self.node_settings.deleted)

    @mock.patch('website.addons.dataverse.model.AddonDataverseUserSettings.clear')
    def test_delete(self, mock_clear):

        self.user_settings.delete()

        assert_true(self.user_settings.deleted)
        mock_clear.assert_called_once_with(delete=True)


class TestDataverseNodeSettings(DataverseAddonTestCase):

    def test_deauthorize(self):

        self.node_settings.deauthorize(Auth(self.user))

        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user_settings)

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

    @mock.patch('website.addons.dataverse.model.connect')
    @mock.patch('website.addons.dataverse.model.get_dataverse')
    def test_to_json_unreleased_dataverse(self, mock_dataverse, mock_connection):
        mock_connection.return_value = create_mock_connection()
        mock_dataverse.return_value = None #create_mock_dataverse()
        type(mock_dataverse).is_released = mock.PropertyMock(return_value=False)

        json = self.node_settings.to_json(self.user)

        assert_true(json['authorized'])
        assert_true(json['connected'])
        assert_true(json['user_dataverse_connected'])

        assert_equal(self.user_settings.dataverse_username,
                     json['authorized_dataverse_user'])
        assert_equal(None, json['dataverse'])
        assert_equal(None, json['study_hdl'])
        assert_equal(3, len(json['dataverses']))
        assert_false(json['study_names'])

        assert_not_in('dataverse_url', json)
        assert_not_in('study_url', json)


class TestNodeSettingsCallbacks(DataverseAddonTestCase):

    def test_after_fork_by_authorized_dataverse_user(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=self.user_settings.owner
        )
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_dataverse_user(self):
        fork = ProjectFactory()
        user = UserFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=user,
            save=True
        )
        assert_is(clone.user_settings, None)

    def test_before_fork(self):
        node = ProjectFactory()
        message = self.node_settings.before_fork(node, self.user)
        assert_true(message)

    def test_before_remove_contributor_message(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.user)
        assert_true(message)
        assert_in(self.user.fullname, message)
        assert_in(self.project.project_or_component, message)

    def test_after_remove_authorized_dataverse_user(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)