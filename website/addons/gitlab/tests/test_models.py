import mock
from nose.tools import *

from website.addons.gitlab.tests import GitlabTestCase

from website.addons.base import AddonError
from website.addons.gitlab.model import GitlabGuidFile
from website.addons.gitlab.tests.factories import GitlabGuidFileFactory


class TestUserSettings(GitlabTestCase):

    @mock.patch('website.addons.gitlab.model.client.edituser')
    def test_password_callback(self, mock_edit_user):
        self.user.set_password('supersecret')
        mock_edit_user.assert_called_with(
            self.user_settings.user_id,
            encrypted_password=self.user.password
        )


class TestNodeSettings(GitlabTestCase):

    def test_get_or_create_exists(self):
        guid = GitlabGuidFileFactory(node=self.project)
        guid_count = GitlabGuidFile.find().count()
        retrieved_guid = GitlabGuidFile.get_or_create(
            self.node_settings, guid.path, 'master'
        )
        assert_equal(
            guid._id,
            retrieved_guid._id
        )
        assert_equal(
            GitlabGuidFile.find().count(),
            guid_count
        )

    @mock.patch('website.addons.gitlab.model.client.listrepositorycommits')
    def test_get_or_create_not_exists(self, mock_list):
        mock_list.return_value = True
        guid_count = GitlabGuidFile.find().count()
        retrieved_guid = GitlabGuidFile.get_or_create(
            self.node_settings, 'foo.txt', 'master',
        )
        assert_equal(
            retrieved_guid.node._id,
            self.project._id
        )
        assert_equal(
            retrieved_guid.path,
            'foo.txt'
        )
        assert_equal(
            GitlabGuidFile.find().count(),
            guid_count + 1
        )

    @mock.patch('website.addons.gitlab.model.client.listrepositorycommits')
    def test_get_or_create_not_exists_not_found(self, mock_list):
        mock_list.return_value = []
        with assert_raises(AddonError):
            GitlabGuidFile.get_or_create(
                self.node_settings, 'bar.txt', 'master',
            )

    @mock.patch('website.addons.gitlab.model.client.listrepositorycommits')
    def test_get_or_create_not_exists_gitlab_error(self, mock_list):
        mock_list.side_effect = AddonError('Ack!')
        with assert_raises(AddonError):
            GitlabGuidFile.get_or_create(
                self.node_settings, 'baz.txt', 'master',
            )
