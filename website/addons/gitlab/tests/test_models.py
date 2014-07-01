import mock
from nose.tools import *

import urlparse

from website.addons.gitlab.tests import GitlabTestCase
from website.addons.gitlab.api import GitlabError
from website.addons.gitlab import settings as gitlab_settings

from website.addons.base import AddonError
from website.addons.gitlab.model import GitlabGuidFile
from website.addons.gitlab.api import client
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

    def test_hook_url(self):
        relative_url = self.node_lookup.api_url_for('gitlab_hook_callback')
        absolute_url = urlparse.urljoin(
            gitlab_settings.HOOK_DOMAIN,
            relative_url
        )
        assert_equal(
            self.node_settings.hook_url,
            absolute_url
        )

    @mock.patch('website.addons.gitlab.model.client.addprojecthook')
    def test_add_hook(self, mock_add_hook):
        mock_add_hook.return_value = {
            'id': 1,
        }
        self.node_settings.add_hook()
        mock_add_hook.assert_called_with(
            self.node_settings.project_id,
            self.node_settings.hook_url
        )

    def test_add_hook_already_exists(self):
        self.node_settings.hook_id = 1
        with assert_raises(AddonError):
            self.node_settings.add_hook()

    @mock.patch('website.addons.gitlab.model.client.addprojecthook')
    def test_add_hook_gitlab_error(self, mock_add_hook):
        mock_add_hook.side_effect = GitlabError('Disaster')
        with assert_raises(AddonError):
            self.node_settings.add_hook()

    @mock.patch('website.addons.gitlab.model.client.deleteprojecthook')
    def test_remove_hook(self, mock_delete_hook):
        self.node_settings.hook_id = 1
        self.node_settings.remove_hook()
        mock_delete_hook.assert_called_with(
            self.node_settings.project_id,
            1
        )
        assert_equal(
            self.node_settings.hook_id,
            None
        )

    def test_remove_hook_none_exists(self):
        with assert_raises(AddonError):
            self.node_settings.remove_hook()

    @mock.patch('website.addons.gitlab.model.client.deleteprojecthook')
    def test_remove_hook_gitlab_error(self, mock_delete_hook):
        mock_delete_hook.side_effect = GitlabError('Catastrophe')
        with assert_raises(AddonError):
            self.node_settings.remove_hook()

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
            self.node_settings, 'foo.txt', 'master', client=client,
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
                self.node_settings, 'bar.txt', 'master', client=client,
            )

    @mock.patch('website.addons.gitlab.model.client.listrepositorycommits')
    def test_get_or_create_not_exists_gitlab_error(self, mock_list):
        mock_list.side_effect = AddonError('Ack!')
        with assert_raises(AddonError):
            GitlabGuidFile.get_or_create(
                self.node_settings, 'baz.txt', 'master', client=client,
            )
