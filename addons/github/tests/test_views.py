from github3.session import GitHubSession
from rest_framework import status as http_status
import unittest
from django.utils import timezone
from github3.repos.branch import Branch
from json import dumps
from unittest import mock
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
from osf_tests.factories import ProjectFactory, UserFactory, AuthUserFactory, DraftRegistrationFactory

pytestmark = pytest.mark.django_db


class TestGitHubAuthViews(GitHubAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    @mock.patch(
        'addons.github.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super().test_delete_external_account()


class TestGitHubConfigViews(GitHubAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = None
    Serializer = GitHubSerializer
    client = GitHubClient

    ## Overrides ##

    def setUp(self):
        super().setUp()
        self.mock_api_user = mock.patch('addons.github.api.GitHubClient.user')
        self.mock_api_credentials_are_valid = mock.patch('addons.github.api.GitHubClient.check_authorization', return_value=True)
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_credentials_are_valid.start()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super().tearDown()

    def test_folder_list(self):
        # GH only lists root folder (repos), this test is superfluous
        pass

    @mock.patch('addons.github.models.NodeSettings.add_hook')
    @mock.patch('addons.github.views.GitHubClient.repo')
    def test_set_config(self, mock_repo, mock_add_hook):
        # GH selects repos, not folders, so this needs to be overriden
        mock_repo.return_value = 'repo_name'
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_set_config')
        res = self.app.post(url, json={
            'github_user': 'octocat',
            'github_repo': 'repo_name',
        }, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        self.project.reload()
        assert self.project.logs.latest().action == \
            f'{self.ADDON_SHORT_NAME}_repo_linked'
        mock_add_hook.assert_called_once_with(save=False)


# TODO: Test remaining CRUD methods
# TODO: Test exception handling
class TestCRUD(OsfTestCase):

    def setUp(self):
        super().setUp()
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
        super().setUp()
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
        assert branch == github_mock.repo.return_value.default_branch
        assert sha == self._get_sha_for_branch(branch=None)  # Get refs for default branch
        assert branches == github_mock.branches.return_value

    @mock.patch('addons.github.api.GitHubClient.branches')
    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_get_refs_branch(self, mock_repo, mock_branches):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value
        mock_branches.return_value = github_mock.branches.return_value
        branch, sha, branches = utils.get_refs(self.node_settings, 'master')
        assert branch == 'master'
        branch_sha = self._get_sha_for_branch('master')
        assert sha == branch_sha
        assert branches == github_mock.branches.return_value

    def test_before_fork(self):
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert len(res.json['prompts']) == 1

    def test_get_refs_sha_no_branch(self):
        with pytest.raises(HTTPError):
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
            with pytest.raises(HTTPError):
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
        assert not check_permissions(self.node_settings, non_authenticated_auth, connection, branch)

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
        assert not check_permissions(self.node_settings, self.consolidated_auth, connection, branch, repo=mock_repository)

    # make a branch with a different commit than the commit being passed into check_permissions
    @mock.patch('addons.github.models.UserSettings.has_auth')
    def test_permissions_not_head(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        mock_branch = mock.NonCallableMock()
        mock_branch.commit.sha = '67890'
        sha = '12345'
        assert not check_permissions(self.node_settings, self.consolidated_auth, connection, mock_branch, sha=sha)

    # # make sure permissions are not granted for editing a registration
    @mock.patch('addons.github.models.UserSettings.has_auth')
    def test_permissions(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        with mock.patch('osf.models.node.AbstractNode.is_registration', new_callable=mock.PropertyMock) as mock_is_reg:
            mock_is_reg.return_value = True
            assert not check_permissions(self.node_settings, self.consolidated_auth, connection, 'master')

    def check_hook_urls(self, urls, node, path, sha):
        url = node.web_url_for('addon_view_or_download_file', path=path, provider='github')
        expected_urls = {
            'view': f'{url}?ref={sha}',
            'download': f'{url}?action=download&ref={sha}'
        }

        assert urls['view'] == expected_urls['view']
        assert urls['download'] == expected_urls['download']

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_add_file_not_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/github/hook/'
        timestamp = str(timezone.now())
        self.app.post(
            url,
            json={
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
            follow_redirects=True
        )
        self.project.reload()
        assert self.project.logs.latest().action == 'github_file_added'
        urls = self.project.logs.latest().params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_modify_file_not_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/github/hook/'
        timestamp = str(timezone.now())
        self.app.post(
            url,
            json={'test': True,
                 'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                              'distinct': True,
                              'message': ' foo',
                              'timestamp': timestamp,
                              'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                              'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                              'committer': {'name': 'Testor', 'email': 'test@osf.io',
                                            'username': 'tester'},
                              'added': [], 'removed':[], 'modified':['PRJWN3TV']}]},
            content_type='application/json')
        self.project.reload()
        assert self.project.logs.latest().action == 'github_file_updated'
        urls = self.project.logs.latest().params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_remove_file_not_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/github/hook/'
        timestamp = str(timezone.now())
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'foo',
                          'timestamp': timestamp,
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed': ['PRJWN3TV'], 'modified':[]}]},
            content_type='application/json')
        self.project.reload()
        assert self.project.logs.latest().action == 'github_file_removed'
        urls = self.project.logs.latest().params['urls']
        assert urls == {}

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_add_file_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/github/hook/'
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Added via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': ['PRJWN3TV'], 'removed':[], 'modified':[]}]},
            content_type='application/json')
        self.project.reload()
        assert self.project.logs.latest().action != 'github_file_added'

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_modify_file_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/github/hook/'
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Updated via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed':[], 'modified':['PRJWN3TV']}]},
            content_type='application/json')
        self.project.reload()
        assert self.project.logs.latest().action != 'github_file_updated'

    @mock.patch('addons.github.views.verify_hook_signature')
    def test_hook_callback_remove_file_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/github/hook/'
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Deleted via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed':['PRJWN3TV'], 'modified':[]}]},
            content_type='application/json', follow_redirects=True)
        self.project.reload()
        assert self.project.logs.latest().action != 'github_file_removed'


class TestRegistrationsWithGithub(OsfTestCase):

    def setUp(self):
        super().setUp()
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


USER = 'octo-cat'
REPO_AUTHOR = {
    'name': USER,
    'email': 'njqpw@osf.io',
    'avatar_url': 'https://gravatar.com/avatar/c74f9cfd7776305a82ede0b765d65402?d=https%3A%2F'
                  '%2Fidenticons.github.com%2F3959fe3bcd263a12c28ae86a66ec75ef.png&r=x',
    'events_url': 'https://api.github.com/users/{user}/events{{/privacy}}',
    'followers_url': 'https://api.github.com/users/{user}/followers',
    'following_url': 'https://api.github.com/users/{user}/following{{/other_user}}',
    'gists_url': 'https://api.github.com/users/{user}/gists{{/gist_id}}',
    'gravatar_id': 'c74f9cfd7776305a82ede0b765d65402',
    'html_url': 'https://github.com/{user}',
    'id': 2379650,
    'login': '{user}',
    'organizations_url': 'https://api.github.com/users/{user}/orgs',
    'received_events_url': 'https://api.github.com/users/{user}/received_events',
    'repos_url': 'https://api.github.com/users/{user}/repos',
    'site_admin': False,
    'starred_url': 'https://api.github.com/users/{user}/starred{{/owner}}{{/repo}}',
    'subscriptions_url': 'https://api.github.com/users/{'
                         'user}/subscriptions',
    'type': 'User',
    'url': 'https://api.github.com/users/{user}'
}
REPO_COMMIT = {
    'ETag': '',
    'Last-Modified': '',
    'url': '',
    'author': REPO_AUTHOR,
    'committer': {'name': '{user}', 'email': '{user}@osf.io',
                  'username': 'tester'},
    'message': 'Fixed error',
    'tree': {'url': 'https://docs.github.com/en/rest/git/trees',
             'sha': 'e22d92d5d90bb8f9695e9a5e2e2311a5c1997230'},
}
REPO_PARENTS = [
    '12345',
    'https://api.example.com/entities/67890',
    'another-entity-id'
]


class TestGithubSettings(OsfTestCase):

    def setUp(self):
        super().setUp()
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
        self.app.post(
            url,
            json={
                'github_user': 'queen',
                'github_repo': 'night at the opera',
            },
            auth=self.auth
        )

        self.project.reload()
        self.node_settings.reload()

        assert self.node_settings.user == 'queen'
        assert self.node_settings.repo == 'night at the opera'
        assert self.project.logs.latest().action == 'github_repo_linked'
        mock_add_hook.assert_called_once_with(save=False)

    @mock.patch('addons.github.models.NodeSettings.add_hook')
    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_link_repo_no_change(self, mock_repo, mock_add_hook):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value

        log_count = self.project.logs.count()

        url = self.project.api_url + 'github/settings/'
        self.app.post(
            url,
            json={
                'github_user': 'Queen',
                'github_repo': 'Sheer-Heart-Attack',
            },
            auth=self.auth
        )

        self.project.reload()
        self.node_settings.reload()

        assert self.project.logs.count() == log_count
        assert not mock_add_hook.called

    @mock.patch('addons.github.api.GitHubClient.repo')
    def test_link_repo_non_existent(self, mock_repo):
        mock_repo.return_value = None

        url = self.project.api_url + 'github/settings/'
        res = self.app.post(
            url,
            json={
                'github_user': 'queen',
                'github_repo': 'night at the opera',
            },
            auth=self.auth,
        )

        assert res.status_code == 400

    @mock.patch('addons.github.api.GitHubClient.branches')
    def test_link_repo_registration(self, mock_branches):
        session = GitHubSession()
        mock_branches.return_value = [
            Branch.from_json(dumps({
                'name': 'master',
                'commit': {
                    'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
                    'url': f'https://api.github.com/repos/{USER}/mock-repo/commits'
                           f'/444a74d0d90a4aea744dacb31a14f87b5c30759c',
                    'author': REPO_AUTHOR,
                    'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
                    'commit': REPO_COMMIT,
                    'committer': REPO_AUTHOR,
                    'html_url': 'https://github.com/{user}',
                    'parents': REPO_PARENTS,

                }, '_links': [{
                    'rel': 'self',
                    'href': 'https://api.example.com/entities/12345'
                }],
                'protected': True,
                'protection': 'public',
                'protection_url': 'https://api.example.com/docs/protection',
                'name': 'no-bundle'}), session=session),
            Branch.from_json(dumps({
                'name': 'develop',
                'commit': {
                    'sha': '444a74d0d90a4aea744dacb31a14f87b5c30759c',
                    'url': f'https://api.github.com/repos/{USER}/mock-repo/commits'
                           f'/444a74d0d90a4aea744dacb31a14f87b5c30759c',
                    'author': REPO_AUTHOR,
                    'comments_url': 'https://api.github.com/repos/{user}/mock-repo/comments{{/number}}',
                    'commit': REPO_COMMIT,
                    'committer': REPO_AUTHOR,
                    'html_url': 'https://github.com/{user}',
                    'parents': REPO_PARENTS,

                }, '_links': [{
                    'rel': 'self',
                    'href': 'https://api.example.com/entities/12345'
                }],
                'protected': True,
                'protection': 'public',
                'protection_url': 'https://api.example.com/docs/protection',
                'name': 'no-bundle'}), session=session)
        ]

        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=self.consolidated_auth,
            draft_registration=DraftRegistrationFactory(branched_from=self.project)
        )

        url = registration.api_url + 'github/settings/'
        res = self.app.post(
            url,
            json={
                'github_user': 'queen',
                'github_repo': 'night at the opera',
            },
            auth=self.auth,
        )

        assert res.status_code == 400

    @mock.patch('addons.github.models.NodeSettings.delete_hook')
    def test_deauthorize(self, mock_delete_hook):
        url = self.project.api_url + 'github/user_auth/'

        self.app.delete(url, auth=self.auth, follow_redirects=True)

        self.project.reload()
        self.node_settings.reload()
        assert self.node_settings.user is None
        assert self.node_settings.repo is None
        assert self.node_settings.user_settings is None

        assert self.project.logs.latest().action == 'github_node_deauthorized'


if __name__ == '__main__':
    unittest.main()
