from unittest import mock
import pytest
import unittest
from json import dumps

from addons.base.tests.models import (OAuthAddonNodeSettingsTestSuiteMixin,
                                      OAuthAddonUserSettingTestSuiteMixin)
from addons.github.models import NodeSettings
from addons.github.tests import factories
from osf_tests.factories import ProjectFactory, UserFactory, DraftRegistrationFactory


from github3 import GitHubError
from github3.repos import Repository
from github3.session import GitHubSession

from tests.base import OsfTestCase, get_default_metaschema

from framework.auth import Auth
from addons.base import exceptions
from addons.github.exceptions import NotFoundError

from .utils import create_mock_github

pytestmark = pytest.mark.django_db

TEST_REPO_DATA = {
    'name': 'test',
    'id': '12345',
    'archive_url': 'https://api.github.com/repos/{user}/mock-repo/{{archive_format}}{{/ref}}',
    'assignees_url': 'https://api.github.com/repos/{user}/mock-repo/assignees{{/user}}',
    'blobs_url': 'https://api.github.com/repos/{user}/mock-repo/git/blobs{{/sha}}',
    'branches_url': 'https://api.github.com/repos/{user}/mock-repo/branches{{/bra.format('
                    'user=user)nch}}',
    'clone_url': 'https://github.com/{user}/mock-repo.git',
    'collaborators_url': 'https://api.github.com/repos/{user}/mock-repo/collaborators{{/collaborator}}',
    'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
    'commits_url': 'https://api.github.com/repos/{user}/mock-repo/commits{{/sha}}',
    'compare_url': 'https://api.github.com/repos/{user}/mock-repo/compare/{{base}}...{{head}}',
    'contents_url': 'https://api.github.com/repos/{user}/mock-repo/contents/{{+path}}',
    'contributors_url': 'https://api.github.com/repos/{user}/mock-repo/contributors',
    'created_at': '2013-06-30T18:29:18Z',
    'default_branch': 'dev',
    'description': 'Simple, Pythonic, text processing--Sentiment analysis, part-of-speech tagging, '
                   'noun phrase extraction, translation, and more.',
    'downloads_url': 'https://api.github.com/repos/{user}/mock-repo/downloads',
    'events_url': 'https://api.github.com/repos/{user}/mock-repo/events',
    'fork': False,
    'forks': 89,
    'forks_count': 89,
    'forks_url': 'https://api.github.com/repos/{user}/mock-repo/forks',
    'full_name': '{user}/mock-repo',
    'git_commits_url': 'https://api.github.com/repos/{user}/mock-repo/git/commits{{/sha}}',
    'git_refs_url': 'https://api.github.com/repos/{user}/mock-repo/git/refs{{/sha}}',
    'git_tags_url': 'https://api.github.com/repos/{user}/mock-repo/git/tags{{/sha}}',
    'git_url': 'git://github.com/{user}/mock-repo.git',
    'has_downloads': True,
    'has_issues': True,
    'has_wiki': True,
    'homepage': 'https://mock-repo.readthedocs.org/',
    'hooks_url': 'https://api.github.com/repos/{user}/mock-repo/hooks',
    'html_url': 'https://github.com/{user}/mock-repo',
    'issue_comment_url': 'https://api.github.com/repos/{user}/mock-repo/issues/comments/{{number}}',
    'issue_events_url': 'https://api.github.com/repos/{user}/mock-repo/issues/events{{/number}}',
    'issues_url': 'https://api.github.com/repos/{user}/mock-repo/issues{{/number}}',
    'keys_url': 'https://api.github.com/repos/{user}/mock-repo/keys{{/key_id}}',
    'labels_url': 'https://api.github.com/repos/{user}/mock-repo/labels{{/name}}',
    'language': 'Python',
    'languages_url': 'https://api.github.com/repos/{user}/mock-repo/languages',
    'master_branch': 'dev',
    'merges_url': 'https://api.github.com/repos/{user}/mock-repo/merges',
    'milestones_url': 'https://api.github.com/repos/{user}/mock-repo/milestones{{/number}}',
    'mirror_url': None,
    'network_count': 89,
    'notifications_url': 'https://api.github.com/repos/{user}/mock-repo/notifications{{?since,all,'
                         'participating}}',
    'open_issues': 2,
    'open_issues_count': 2,
    'owner': {
        'avatar_url': 'https://gravatar.com/avatar/c74f9cfd7776305a82ede0b765d65402?d=https%3A%2F'
                      '%2Fidenticons.github.com%2F3959fe3bcd263a12c28ae86a66ec75ef.png&r=x',
        'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}',
        'followers_url': 'https://api.github.com/users/{user}/followers',
        'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}',
        'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}',
        'gravatar_id': 'c74f9cfd7776305a82ede0b765d65402',
        'html_url': 'https://github.com/{user}',
        'id': 2379650,
        'login': 'test name',
        'organizations_url': 'https://api.github.com/users/{user}/orgs',
        'received_events_url': 'https://api.github.com/users/{user}/received_events',
        'repos_url': 'https://api.github.com/users/{user}/repos',
        'site_admin': False,
        'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}',
        'subscriptions_url': 'https://api.github.com/users/{user}/subscriptions',
        'type': 'User',
        'url': 'https://api.github.com/users/{user}'
    },
    'private': False,
    'pulls_url': 'https://api.github.com/repos/{user}/mock-repo/pulls{{/number}}',
    'pushed_at': '2013-12-30T16:05:54Z',
    'releases_url': 'https://api.github.com/repos/{user}/mock-repo/releases{{/id}}',
    'size': 8717,
    'ssh_url': 'git@github.com:{user}/mock-repo.git',
    'stargazers_count': 1469,
    'stargazers_url': 'https://api.github.com/repos/{user}/mock-repo/stargazers',
    'statuses_url': 'https://api.github.com/repos/{user}/mock-repo/statuses/{{sha}}',
    'subscribers_count': 86,
    'subscribers_url': 'https://api.github.com/repos/{user}/mock-repo/subscribers',
    'subscription_url': 'https://api.github.com/repos/{user}/mock-repo/subscription',
    'svn_url': 'https://github.com/{user}/mock-repo',
    'tags_url': 'https://api.github.com/repos/{user}/mock-repo/tags',
    'teams_url': 'https://api.github.com/repos/{user}/mock-repo/teams',
    'trees_url': 'https://api.github.com/repos/{user}/mock-repo/git/trees{{/sha}}',
    'updated_at': '2014-01-12T21:23:50Z',
    'url': 'https://api.github.com/repos/{user}/mock-repo',
    'watchers': 1469,
    'watchers_count': 1469,
    'permissions': {'push': True},
    'deployments_url': 'https://api.github.com/repos',
    'archived': {},
    'has_pages': False,
    'has_projects': False,
}


class TestNodeSettings(OAuthAddonNodeSettingsTestSuiteMixin, unittest.TestCase):
    short_name = 'github'
    full_name = 'GitHub'
    ExternalAccountFactory = factories.GitHubAccountFactory

    NodeSettingsFactory = factories.GitHubNodeSettingsFactory
    NodeSettingsClass = NodeSettings
    UserSettingsFactory = factories.GitHubUserSettingsFactory

    ## Mixin Overrides ##

    def _node_settings_class_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'repo': 'mock',
            'user': 'abc',
            'owner': self.node
        }

    def test_set_folder(self):
        # GitHub doesn't use folderpicker, and the nodesettings model
        # does not need a `set_repo` method
        pass

    def test_serialize_settings(self):
        # GitHub's serialized_settings are a little different from
        # common storage addons.
        settings = self.node_settings.serialize_waterbutler_settings()
        expected = {'owner': self.node_settings.user, 'repo': self.node_settings.repo}
        assert settings == expected

    @mock.patch(
        'addons.github.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_complete_has_auth_not_verified(self):
        super().test_complete_has_auth_not_verified()

    @mock.patch('addons.github.api.GitHubClient.repos')
    @mock.patch('addons.github.api.GitHubClient.check_authorization')
    def test_to_json(self, mock_repos, mock_check_authorization):
        mock_repos.return_value = {}
        super().test_to_json()

    @mock.patch('addons.github.api.GitHubClient.repos')
    @mock.patch('addons.github.api.GitHubClient.check_authorization')
    def test_to_json_user_is_owner(self, mock_check_authorization, mock_repos):
        mock_check_authorization.return_value = True
        mock_repos.return_value = {}
        result = self.node_settings.to_json(self.user)
        assert result['user_has_auth']
        assert result['github_user'] == 'abc'
        assert result['is_owner']
        assert result['valid_credentials']
        assert result.get('repo_names', None) == []

    @mock.patch('addons.github.api.GitHubClient.repos')
    @mock.patch('addons.github.api.GitHubClient.check_authorization')
    def test_to_json_user_is_not_owner(self, mock_check_authorization, mock_repos):
        mock_check_authorization.return_value = True
        mock_repos.return_value = {}
        not_owner = UserFactory()
        result = self.node_settings.to_json(not_owner)
        assert not result['user_has_auth']
        assert result['github_user'] == 'abc'
        assert not result['is_owner']
        assert result['valid_credentials']
        assert result.get('repo_names') is None

    @mock.patch('addons.github.api.GitHubClient.repos')
    @mock.patch('addons.github.api.GitHubClient.check_authorization')
    def test_get_folders(self, mock_check_authorization, mock_repos):
        session = GitHubSession()
        mock_repos.return_value = [Repository.from_json(dumps(TEST_REPO_DATA), session=session)
                                   ]
        result = self.node_settings.get_folders()

        assert len(result) == 1
        assert result[0]['id'] == '12345'
        assert result[0]['name'] == 'test'
        assert result[0]['path'] == 'test name/test'
        assert result[0]['kind'] == 'repo'

    @mock.patch('addons.github.api.GitHubClient.repos')
    @mock.patch('addons.github.api.GitHubClient.check_authorization')
    def test_get_folders_not_have_auth(self, mock_repos, mock_check_authorization):
        session = GitHubSession()
        mock_repos.return_value = [Repository.from_json(dumps(TEST_REPO_DATA), session=session)
                                   ]
        self.node_settings.user_settings = None
        with pytest.raises(exceptions.InvalidAuthError):
            self.node_settings.get_folders()


class TestUserSettings(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    short_name = 'github'
    full_name = 'GitHub'
    ExternalAccountFactory = factories.GitHubAccountFactory

    def test_public_id(self):
        assert self.user.external_accounts.first().display_name == self.user_settings.public_id


class TestCallbacks(OsfTestCase):

    def setUp(self):
        super().setUp()

        self.project = ProjectFactory()
        self.consolidated_auth = Auth(self.project.creator)
        self.project.creator.save()
        self.non_authenticator = UserFactory()
        self.non_authenticator.save()
        self.project.save()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )

        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')
        self.external_account = factories.GitHubAccountFactory()
        self.project.creator.external_accounts.add(self.external_account)
        self.project.creator.save()
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.external_account = self.external_account
        self.node_settings.save()
        self.node_settings.set_auth
        self.user_settings.oauth_grants[self.project._id] = {self.external_account._id: []}
        self.user_settings.save()

    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_before_make_public(self, mock_repo):
        mock_repo.side_effect = NotFoundError

        result = self.node_settings.before_make_public(self.project)
        assert result is None

    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_before_page_load_osf_public_gh_public(self, mock_repo):
        session = GitHubSession()
        self.project.is_public = True
        self.project.save()
        mock_repo.return_value = Repository.from_json(dumps(TEST_REPO_DATA), session=session)
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert not message

    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_before_page_load_osf_public_gh_private(self, mock_repo):
        session = GitHubSession()
        self.project.is_public = True
        self.project.save()
        mock_data = TEST_REPO_DATA.copy()
        mock_data['private'] = True
        mock_repo.return_value = Repository.from_json(dumps(mock_data), session=session)
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert message

    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_before_page_load_osf_private_gh_public(self, mock_repo):
        session = GitHubSession()
        mock_repo.return_value = Repository.from_json(dumps(TEST_REPO_DATA), session=session)
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert message

    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_before_page_load_osf_private_gh_private(self, mock_repo):
        session = GitHubSession()
        mock_data = TEST_REPO_DATA.copy()
        mock_data['private'] = True
        mock_repo.return_value = Repository.from_json(dumps(mock_data), session=session)
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_repo.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        assert not message

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
        assert not registration.has_addon('github')


class TestGithubNodeSettings(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        self.user.add_addon('github')
        self.user_settings = self.user.get_addon('github')
        self.external_account = factories.GitHubAccountFactory()
        self.user_settings.owner.external_accounts.add(self.external_account)
        self.user_settings.owner.save()
        self.node_settings = factories.GitHubNodeSettingsFactory(user_settings=self.user_settings)

    @mock.patch('addons.github.api.GitHubClient.delete_hook')
    def test_delete_hook(self, mock_delete_hook):
        self.node_settings.hook_id = 'hook'
        self.node_settings.save()
        args = (
            self.node_settings.user,
            self.node_settings.repo,
            self.node_settings.hook_id,
        )
        res = self.node_settings.delete_hook()
        assert res
        mock_delete_hook.assert_called_with(*args)

    @mock.patch('addons.github.api.GitHubClient.delete_hook')
    def test_delete_hook_no_hook(self, mock_delete_hook):
        res = self.node_settings.delete_hook()
        assert not res
        assert not mock_delete_hook.called

    @mock.patch('addons.github.api.GitHubClient.delete_hook')
    def test_delete_hook_not_found(self, mock_delete_hook):
        self.node_settings.hook_id = 'hook'
        self.node_settings.save()
        mock_delete_hook.side_effect = NotFoundError
        args = (
            self.node_settings.user,
            self.node_settings.repo,
            self.node_settings.hook_id,
        )
        res = self.node_settings.delete_hook()
        assert not res
        mock_delete_hook.assert_called_with(*args)

    @mock.patch('addons.github.api.GitHubClient.delete_hook')
    def test_delete_hook_error(self, mock_delete_hook):
        self.node_settings.hook_id = 'hook'
        self.node_settings.save()
        mock_delete_hook.side_effect = GitHubError(mock.Mock())
        args = (
            self.node_settings.user,
            self.node_settings.repo,
            self.node_settings.hook_id,
        )
        res = self.node_settings.delete_hook()
        assert not res
        mock_delete_hook.assert_called_with(*args)
