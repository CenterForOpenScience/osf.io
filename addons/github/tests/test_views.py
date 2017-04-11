# -*- coding: utf-8 -*-
import httplib as http
import mock
from nose.tools import assert_equal, assert_false
import pytest
import unittest

from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, UserFactory, AuthUserFactory

from github3.repos.branch import Branch

from framework.auth import Auth

from addons.base.tests.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from addons.github.tests.utils import create_mock_github, GitHubAddonTestCase
from addons.github.tests.factories import GitHubAccountFactory

from addons.github import utils
from addons.github.api import GitHubClient
from addons.github.serializer import GitHubSerializer

pytestmark = pytest.mark.django_db


class TestGitHubAuthViews(GitHubAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    @mock.patch(
        'addons.github.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super(TestGitHubAuthViews, self).test_delete_external_account()


class TestGitHubConfigViews(GitHubAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = None
    Serializer = GitHubSerializer
    client = GitHubClient

    ## Overrides ##

    def setUp(self):
        super(TestGitHubConfigViews, self).setUp()
        self.mock_api_user = mock.patch('addons.github.api.GitHubClient.user')
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super(TestGitHubConfigViews, self).tearDown()

    def test_folder_list(self):
        # GH only lists root folder (repos), this test is superfluous
        pass

    @mock.patch('addons.github.models.NodeSettings.add_hook')
    @mock.patch('addons.github.views.GitHubClient.repo')
    def test_set_config(self, mock_repo, mock_add_hook):
        # GH selects repos, not folders, so this needs to be overriden
        mock_repo.return_value = 'repo_name'
        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.post_json(url, {
            'github_user': 'octocat',
            'github_repo': 'repo_name',
        }, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.project.reload()
        assert_equal(
            self.project.logs.latest().action,
            '{0}_repo_linked'.format(self.ADDON_SHORT_NAME)
        )
        mock_add_hook.assert_called_once()


# TODO: Test remaining CRUD methods
# TODO: Test exception handling
class TestCRUD(OsfTestCase):

    def setUp(self):
        super(TestCRUD, self).setUp()
        self.github = create_mock_github(user='fred', private=False)
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')
        self.node_settings = self.project.get_addon('github')
        self.node_settings.user_settings = self.project.creator.get_addon('github')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = self.github.repo.return_value.owner.login
        self.node_settings.repo = self.github.repo.return_value.name
        self.node_settings.save()


class TestGithubViews(OsfTestCase):

    def setUp(self):
        super(TestGithubViews, self).setUp()
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)

        self.project = ProjectFactory(creator=self.user)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=self.consolidated_auth,
        )
        self.project.creator.add_addon('github')
        self.project.creator.external_accounts.add(GitHubAccountFactory())
        self.project.creator.save()
        self.project.save()
        self.project.add_addon('github', auth=self.consolidated_auth)

        self.github = create_mock_github(user='fred', private=False)

        self.node_settings = self.project.get_addon('github')
        self.node_settings.user_settings = self.project.creator.get_addon('github')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = self.github.repo.return_value.owner.login
        self.node_settings.repo = self.github.repo.return_value.name
        self.node_settings.save()

    def _get_sha_for_branch(self, branch=None, mock_branches=None):
        github_mock = self.github
        if mock_branches is None:
            mock_branches = github_mock.branches
        if branch is None:  # Get default branch name
            branch = self.github.repo.return_value.default_branch
        for each in mock_branches.return_value:
            if each.name == branch:
                branch_sha = each.commit.sha
        return branch_sha

    # Tests for _get_refs
    @mock.patch('addons.github.api.GitHubClient.branches')
    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_get_refs_defaults(self, mock_repo, mock_branches):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value
        mock_branches.return_value = github_mock.branches.return_value
        branch, sha, branches = utils.get_refs(self.node_settings)


class TestRegistrationsWithGithub(OsfTestCase):

    def setUp(self):

        super(TestRegistrationsWithGithub, self).setUp()
        self.project = ProjectFactory()
        self.consolidated_auth = Auth(user=self.project.creator)

        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()


class TestGithubSettings(OsfTestCase):

    def setUp(self):

        super(TestGithubSettings, self).setUp()
        self.github = create_mock_github(user='fred', private=False)
        self.project = ProjectFactory()
        self.auth = self.project.creator.auth
        self.consolidated_auth = Auth(user=self.project.creator)

        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()

    @mock.patch('addons.github.models.NodeSettings.add_hook')
    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_link_repo(self, mock_repo, mock_add_hook):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value

        url = self.project.api_url + 'github/settings/'
        self.app.post_json(
            url,
            {
                'github_user': 'queen',
                'github_repo': 'night at the opera',
            },
            auth=self.auth
        ).maybe_follow()

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.node_settings.user, 'queen')
        assert_equal(self.node_settings.repo, 'night at the opera')
        assert_equal(self.project.logs.latest().action, 'github_repo_linked')
        mock_add_hook.assert_called_once()

    @mock.patch('addons.github.models.NodeSettings.add_hook')
    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_link_repo_no_change(self, mock_repo, mock_add_hook):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value

        log_count = self.project.logs.count()

        url = self.project.api_url + 'github/settings/'
        self.app.post_json(
            url,
            {
                'github_user': 'Queen',
                'github_repo': 'Sheer-Heart-Attack',
            },
            auth=self.auth
        ).maybe_follow()

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.project.logs.count(), log_count)
        assert_false(mock_add_hook.called)

    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_link_repo_non_existent(self, mock_repo):

        mock_repo.return_value = None

        url = self.project.api_url + 'github/settings/'
        res = self.app.post_json(
            url,
            {
                'github_user': 'queen',
                'github_repo': 'night at the opera',
            },
            auth=self.auth,
            expect_errors=True
        ).maybe_follow()

        assert_equal(res.status_code, 400)

    @mock.patch('addons.github.api.GitHubClient.branches')
    def test_link_repo_registration(self, mock_branches):

        mock_branches.return_value = [
            Branch.from_json({
                'name': 'master',
                'commit': {
                    'sha': '6dcb09b5b57875f334f61aebed695e2e4193db5e',
                    'url': 'https://api.github.com/repos/octocat/Hello-World/commits/c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbc',
                }
            }),
            Branch.from_json({
                'name': 'develop',
                'commit': {
                    'sha': '6dcb09b5b57875asdasedawedawedwedaewdwdass',
                    'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                }
            })
        ]

        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=self.consolidated_auth,
            data=''
        )

        url = registration.api_url + 'github/settings/'
        res = self.app.post_json(
            url,
            {
                'github_user': 'queen',
                'github_repo': 'night at the opera',
            },
            auth=self.auth,
            expect_errors=True
        ).maybe_follow()

        assert_equal(res.status_code, 400)

    @mock.patch('addons.github.models.NodeSettings.delete_hook')
    def test_deauthorize(self, mock_delete_hook):

        url = self.project.api_url + 'github/user_auth/'

        self.app.delete(url, auth=self.auth).maybe_follow()

        self.project.reload()
        self.node_settings.reload()
        assert_equal(self.node_settings.user, None)
        assert_equal(self.node_settings.repo, None)
        assert_equal(self.node_settings.user_settings, None)

        assert_equal(self.project.logs.latest().action, 'github_node_deauthorized')


if __name__ == '__main__':
    unittest.main()
