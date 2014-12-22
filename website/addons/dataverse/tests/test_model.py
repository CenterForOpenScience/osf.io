from nose.tools import *
import mock

from tests.factories import UserFactory, ProjectFactory
from framework.auth.decorators import Auth
from website.addons.dataverse.model import (
    AddonDataverseUserSettings, AddonDataverseNodeSettings, DataverseFile
)
from website.addons.dataverse.tests.utils import DataverseAddonTestCase


class TestDataverseFile(DataverseAddonTestCase):

    def test_dataverse_file_url(self):

        # Create some dataverse file
        dvf = DataverseFile(
            node=self.project,
            file_id='12345',
        )
        dvf.save()

        # Assert url is correct
        assert_equal('dataverse/file/12345', dvf.file_url)


class TestDataverseUserSettings(DataverseAddonTestCase):

    def test_has_auth(self):

        # Dataverse has no auth by default
        dataverse = AddonDataverseUserSettings()
        assert_false(dataverse.has_auth)

        # With valid credentials, dataverse is authorized
        dataverse.dataverse_username = 'snowman'
        dataverse.dataverse_password = 'frosty'
        assert_true(dataverse.has_auth)

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

    @mock.patch('website.addons.dataverse.model.AddonDataverseUserSettings.clear')
    def test_delete(self, mock_clear):

        self.user_settings.delete()

        assert_true(self.user_settings.deleted)
        mock_clear.assert_called_once_with()


class TestDataverseNodeSettings(DataverseAddonTestCase):

    def test_fields(self):
        node_settings = AddonDataverseNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'dataverse'))
        assert_true(hasattr(node_settings, 'dataverse_alias'))
        assert_true(hasattr(node_settings, 'study'))
        assert_true(hasattr(node_settings, 'study_hdl'))

    def test_defaults(self):
        node_settings = AddonDataverseNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.dataverse)
        assert_is_none(node_settings.dataverse_alias)
        assert_is_none(node_settings.study)
        assert_is_none(node_settings.study_hdl)

    def test_has_auth(self):
        node_settings = AddonDataverseNodeSettings()
        node_settings.save()
        assert_false(node_settings.has_auth)

        user_settings = AddonDataverseUserSettings()
        user_settings.save()
        node_settings.user_settings = user_settings
        node_settings.save()
        assert_false(node_settings.has_auth)

        user_settings.dataverse_username = 'foo'
        user_settings.dataverse_password = 'bar'
        user_settings.save()
        assert_true(node_settings.has_auth)

    @mock.patch('website.addons.dataverse.model.AddonDataverseNodeSettings.deauthorize')
    def test_delete(self, mock_deauth):

        num_old_logs = len(self.project.logs)

        self.node_settings.delete()

        assert_true(self.node_settings.deleted)
        args, kwargs = mock_deauth.call_args
        assert_equal(kwargs, {'add_log': False})

        # Log was not generated
        self.project.reload()
        assert_equal(len(self.project.logs), num_old_logs)

    def test_set_user_auth(self):
        project = ProjectFactory()
        project.add_addon('dataverse', auth=Auth(self.user))
        node_settings = project.get_addon('dataverse')
        num_old_logs = len(project.logs)

        assert_false(node_settings.user_settings)
        node_settings.set_user_auth(self.user_settings)
        node_settings.save()
        assert_equal(node_settings.user_settings, self.user_settings)

        # Test log
        project.reload()
        assert_equal(len(project.logs), num_old_logs + 1)
        last_log = project.logs[-1]
        assert_equal(last_log.action, 'dataverse_node_authorized')
        assert_equal(last_log.params['node'], project._primary_key)
        assert_is_none(last_log.params['project'])

    def test_deauthorize(self):

        self.node_settings.deauthorize(Auth(self.user))

        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.study_hdl)
        assert_false(self.node_settings.study)
        assert_false(self.node_settings.user_settings)


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
        assert_is_none(clone.user_settings)

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

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.user_settings is None)
        assert_true(self.node_settings.dataverse_alias is None)
        assert_true(self.node_settings.dataverse is None)
        assert_true(self.node_settings.study_hdl is None)
        assert_true(self.node_settings.study is None)
