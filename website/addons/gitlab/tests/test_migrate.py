"""
TODO: Delete once migration is finished
"""

from nose.tools import *
import mock

from tests.factories import UserFactory
from framework.auth.decorators import Auth
from website.addons.gitlab.tests import GitlabTestCase


class TestMigration(GitlabTestCase):

    @mock.patch('website.project.model.status.push_status_message')
    @mock.patch('website.addons.gitlab.model.GitlabNodeSettings.after_add_contributor')
    def setUp(self, mock_after_add, mock_push):
        super(TestMigration, self).setUp()
        user = UserFactory()
        self.project.add_contributor(user)
        self.node_settings._migration_done = True
        self.node_settings.save()

    @mock.patch('website.project.model.status.push_status_message')
    @mock.patch('website.addons.gitlab.model.GitlabNodeSettings.after_add_contributor')
    def test_add_contributor(self, mock_after_add, mock_push):
        user = UserFactory()
        self.project.add_contributor(user)
        assert_false(self.node_settings._migration_done)

    @mock.patch('website.project.model.status.push_status_message')
    @mock.patch('website.addons.gitlab.model.GitlabNodeSettings.after_remove_contributor')
    def test_remove_contributor(self, mock_callback, mock_push):
        mock_callback.return_value = None
        self.project.remove_contributor(
            self.project.contributors[-1],
            auth=Auth(user=self.user)
        )
        assert_false(self.node_settings._migration_done)

    @mock.patch('website.project.model.status.push_status_message')
    @mock.patch('website.addons.gitlab.model.GitlabNodeSettings.after_set_permissions')
    def test_set_permissions(self, mock_after_set, mock_push):
        self.project.set_permissions(self.project.contributors[-1], 'write')
        assert_false(self.node_settings._migration_done)
