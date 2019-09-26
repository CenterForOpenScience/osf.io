# -*- coding: utf-8 -*-
from rest_framework import status as http_status
import unittest

from django.utils import timezone
from github3.repos.branch import Branch
from nose.tools import *  # noqa: F403
from json import dumps
import mock
import pytest

from framework.auth import Auth
from framework.exceptions import HTTPError
from addons.base.tests.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from addons.github.tests.utils import create_mock_github, GitHubAddonTestCase
from addons.github.tests.factories import GitHubAccountFactory
from addons.github import utils
from addons.github.api import GitHubClient
from addons.github.serializer import GitHubSerializer
from addons.github.utils import check_permissions
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, UserFactory, AuthUserFactory

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
        self.mock_api_credentials_are_valid = mock.patch('addons.github.api.GitHubClient.check_authorization', return_value=True)
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_credentials_are_valid.start()
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
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        self.project.reload()
        assert_equal(
            self.project.logs.latest().action,
            '{0}_repo_linked'.format(self.ADDON_SHORT_NAME)
        )
        mock_add_hook.assert_called_once_with(save=False)


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
        assert_equal(
            branch,
            github_mock.repo.return_value.default_branch
        )
        assert_equal(sha, self._get_sha_for_branch(branch=None))  # Get refs for default branch
        assert_equal(
            branches,
            github_mock.branches.return_value
        )

    @mock.patch('addons.github.api.GitHubClient.branches')
    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_get_refs_branch(self, mock_repo, mock_branches):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value
        mock_branches.return_value = github_mock.branches.return_value
        branch, sha, branches = utils.get_refs(self.node_settings, 'master')
        assert_equal(branch, 'master')
        branch_sha = self._get_sha_for_branch('master')
        assert_equal(sha, branch_sha)
        assert_equal(
            branches,
            github_mock.branches.return_value
        )

    def test_before_fork(self):
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(len(res.json['prompts']), 1)

    def test_get_refs_sha_no_branch(self):
        with assert_raises(HTTPError):
            utils.get_refs(self.node_settings, sha='12345')

    def test_get_refs_registered_missing_branch(self):
        github_mock = self.github
        self.node_settings.registration_data = {
            'branches': [
                branch.as_json()
                for branch in github_mock.branches.return_value
            ]
        }
        with mock.patch('osf.models.node.AbstractNode.is_registration', new_callable=mock.PropertyMock) as mock_is_reg:
            mock_is_reg.return_value = True
            with assert_raises(HTTPError):
                utils.get_refs(self.node_settings, branch='nothere')

    # Tests for _check_permissions
    # make a user with no authorization; make sure check_permissions returns false
    def test_permissions_no_auth(self):
        github_mock = self.github
        # project is set to private right now
        connection = github_mock
        non_authenticated_user = UserFactory()
        non_authenticated_auth = Auth(user=non_authenticated_user)
        branch = 'master'
        assert_false(check_permissions(self.node_settings, non_authenticated_auth, connection, branch))

    # make a repository that doesn't allow push access for this user;
    # make sure check_permissions returns false
    @mock.patch('addons.github.models.UserSettings.has_auth')
    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_permissions_no_access(self, mock_repo, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        branch = 'master'
        mock_repository = mock.NonCallableMock()
        mock_repository.user = 'fred'
        mock_repository.repo = 'mock-repo'
        mock_repository.permissions = dict(push=False)
        mock_repo.return_value = mock_repository
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, branch, repo=mock_repository))

    # make a branch with a different commit than the commit being passed into check_permissions
    @mock.patch('addons.github.models.UserSettings.has_auth')
    def test_permissions_not_head(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        mock_branch = mock.NonCallableMock()
        mock_branch.commit.sha = '67890'
        sha = '12345'
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, mock_branch, sha=sha))

    # # make sure permissions are not granted for editing a registration
    @mock.patch('addons.github.models.UserSettings.has_auth')
    def test_permissions(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        with mock.patch('osf.models.node.AbstractNode.is_registration', new_callable=mock.PropertyMock) as mock_is_reg:
            mock_is_reg.return_value = True
            assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, 'master'))

    def check_hook_urls(self, urls, node, path, sha):
        url = node.web_url_for('addon_view_or_download_file', path=path, provider='github')
        expected_urls = {
            'view': '{0}?ref={1}'.format(url, sha),
            'download': '{0}?action=download&ref={1}'.format(url, sha)
        }

        assert_equal(urls['view'], expected_urls['view'])
        assert_equal(urls['download'], expected_urls['download'])

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_add_file_not_thro_osf(self, mock_verify):
        url = '/api/v1/project/{0}/github/hook/'.format(self.project._id)
        timestamp = str(timezone.now())
        self.app.post_json(
            url,
            {
                'test': True,
                'commits': [{
                    'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                    'distinct': True,
                    'message': 'foo',
                    'timestamp': timestamp,
                    'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                    'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                    'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                    'added': ['PRJWN3TV'],
                    'removed': [],
                    'modified': [],
                }]
            },
            content_type='application/json',
        ).maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs.latest().action, 'github_file_added')
        urls = self.project.logs.latest().params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_modify_file_not_thro_osf(self, mock_verify):
        url = '/api/v1/project/{0}/github/hook/'.format(self.project._id)
        timestamp = str(timezone.now())
        self.app.post_json(
            url,
            {'test': True,
                 'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                              'distinct': True,
                              'message': ' foo',
                              'timestamp': timestamp,
                              'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                              'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                              'committer': {'name': 'Testor', 'email': 'test@osf.io',
                                            'username': 'tester'},
                              'added': [], 'removed':[], 'modified':['PRJWN3TV']}]},
            content_type='application/json').maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs.latest().action, 'github_file_updated')
        urls = self.project.logs.latest().params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_remove_file_not_thro_osf(self, mock_verify):
        url = '/api/v1/project/{0}/github/hook/'.format(self.project._id)
        timestamp = str(timezone.now())
        self.app.post_json(
            url,
            {'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'foo',
                          'timestamp': timestamp,
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed': ['PRJWN3TV'], 'modified':[]}]},
            content_type='application/json').maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs.latest().action, 'github_file_removed')
        urls = self.project.logs.latest().params['urls']
        assert_equal(urls, {})

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_add_file_thro_osf(self, mock_verify):
        url = '/api/v1/project/{0}/github/hook/'.format(self.project._id)
        self.app.post_json(
            url,
            {'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Added via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': ['PRJWN3TV'], 'removed':[], 'modified':[]}]},
            content_type='application/json').maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs.latest().action, 'github_file_added')

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_modify_file_thro_osf(self, mock_verify):
        url = '/api/v1/project/{0}/github/hook/'.format(self.project._id)
        self.app.post_json(
            url,
            {'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Updated via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed':[], 'modified':['PRJWN3TV']}]},
            content_type='application/json').maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs.latest().action, 'github_file_updated')

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_remove_file_thro_osf(self, mock_verify):
        url = '/api/v1/project/{0}/github/hook/'.format(self.project._id)
        self.app.post_json(
            url,
            {'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Deleted via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed':['PRJWN3TV'], 'modified':[]}]},
            content_type='application/json').maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs.latest().action, 'github_file_removed')


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
        mock_add_hook.assert_called_once_with(save=False)

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
            Branch.from_json(dumps({
                'name': 'master',
                'commit': {
                    'sha': '6dcb09b5b57875f334f61aebed695e2e4193db5e',
                    'url': 'https://api.github.com/repos/octocat/Hello-World/commits/c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbc',
                }
            })),
            Branch.from_json(dumps({
                'name': 'develop',
                'commit': {
                    'sha': '6dcb09b5b57875asdasedawedawedwedaewdwdass',
                    'url': 'https://api.github.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                }
            }))
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
