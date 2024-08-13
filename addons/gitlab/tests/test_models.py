from unittest import mock
import pytest
import unittest

from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, UserFactory, DraftRegistrationFactory

from framework.auth import Auth

from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)
from addons.gitlab.exceptions import NotFoundError
from addons.gitlab.models import NodeSettings
from addons.gitlab.tests.factories import (
    GitLabAccountFactory,
    GitLabNodeSettingsFactory,
    GitLabUserSettingsFactory
)

from .utils import create_mock_gitlab
mock_gitlab = create_mock_gitlab()

pytestmark = pytest.mark.django_db

class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):

    short_name = 'gitlab'
    full_name = 'GitLab'
    ExternalAccountFactory = GitLabAccountFactory

    NodeSettingsFactory = GitLabNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = GitLabUserSettingsFactory

    ## Mixin Overrides ##

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node,
            'repo_id': '123'
        }

    def test_set_folder(self):
        # GitLab doesn't use folderpicker, and the nodesettings model
        # does not need a `set_repo` method
        pass

    def test_serialize_settings(self):
        # GitLab's serialized_settings are a little different from
        # common storage addons.
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'host': 'some-super-secret', 'owner': 'abc', 'repo': 'mock', 'repo_id': '123'}
        assert settings == expected

    @mock.patch(
        'addons.gitlab.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_complete_has_auth_not_verified(self):
        super().test_complete_has_auth_not_verified()

    @mock.patch('addons.gitlab.api.GitLabClient.repos')
    def test_to_json(self, mock_repos):
        mock_repos.return_value = {}
        super().test_to_json()

    @mock.patch('addons.gitlab.api.GitLabClient.repos')
    def test_to_json_user_is_owner(self, mock_repos):
        mock_repos.return_value = {}
        result = self.node_settings.to_json(self.user)
        assert result['user_has_auth']
        assert result['gitlab_user'] == 'abc'
        assert result['is_owner']
        assert result['valid_credentials']
        assert result.get('gitlab_repo', None) == 'mock'

    @mock.patch('addons.gitlab.api.GitLabClient.repos')
    def test_to_json_user_is_not_owner(self, mock_repos):
        mock_repos.return_value = {}
        not_owner = UserFactory()
        result = self.node_settings.to_json(not_owner)
        assert not result['user_has_auth']
        assert result['gitlab_user'] == 'abc'
        assert not result['is_owner']
        assert result['valid_credentials']
        assert result.get('repo_names', None) is None


class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):

    short_name = 'gitlab'
    full_name = 'GitLab'
    ExternalAccountFactory = GitLabAccountFactory


class TestCallbacks(OsfTestCase):

    def setUp(self):

        super().setUp()

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(self.project.creator)
        self.project.creator.save()
        self.non_authenticator = UserFactory()
        self.non_authenticator.save()
        self.project.save()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )

        self.project.add_addon('gitlab', auth=self.consolidated_auth)
        self.project.creator.add_addon('gitlab')
        self.external_account = GitLabAccountFactory()
        self.project.creator.external_accounts.add(self.external_account)
        self.project.creator.save()
        self.node_settings = self.project.get_addon('gitlab')
        self.user_settings = self.project.creator.get_addon('gitlab')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.external_account = self.external_account
        self.node_settings.save()
        self.node_settings.set_auth

    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_before_make_public(self, mock_repo):
        mock_repo.side_effect = NotFoundError

        result = self.node_settings.before_make_public(self.project)
        assert result is None

    def test_before_page_load_not_contributor(self):
        message = self.node_settings.before_page_load(self.project, UserFactory())
        assert not message

    def test_before_page_load_not_logged_in(self):
        message = self.node_settings.before_page_load(self.project, None)
        assert not message

    def test_before_remove_contributor_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.project.creator
        )
        assert message

    def test_before_remove_contributor_not_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.non_authenticator
        )
        assert not message

    def test_after_remove_contributor_authenticator_self(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, self.consolidated_auth
        )
        assert self.node_settings.user_settings is None
        assert message
        assert 'You can re-authenticate' not in message

    def test_after_remove_contributor_authenticator_not_self(self):
        auth = Auth(user=self.non_authenticator)
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, auth
        )
        assert self.node_settings.user_settings is None
        assert message
        assert 'You can re-authenticate' in message

    def test_after_remove_contributor_not_authenticator(self):
        self.node_settings.after_remove_contributor(
            self.project, self.non_authenticator, self.consolidated_auth
        )
        assert self.node_settings.user_settings is not None

    def test_after_fork_authenticator(self):
        fork = ProjectFactory()
        clone = self.node_settings.after_fork(
            self.project, fork, self.project.creator,
        )
        assert self.node_settings.user_settings == clone.user_settings

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone = self.node_settings.after_fork(
            self.project, fork, self.non_authenticator,
        )
        assert clone.user_settings is None

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert self.node_settings.user_settings is None


    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.project.creator),
            draft_registration=DraftRegistrationFactory(branched_from=self.project),
        )
        assert not registration.has_addon('gitlab')


class TestGitLabNodeSettings(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.user.add_addon('gitlab')
        self.user_settings = self.user.get_addon('gitlab')
        self.external_account = GitLabAccountFactory()
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.node_settings = GitLabNodeSettingsFactory(user_settings=self.user_settings)

    @mock.patch('addons.gitlab.api.GitLabClient.delete_hook')
    def test_delete_hook_no_hook(self, mock_delete_hook):
        res = self.node_settings.delete_hook()
        assert not res
        assert not mock_delete_hook.called
