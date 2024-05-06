from github3.session import GitHubSession
from rest_framework import status as http_status

from unittest import mock
import datetime
import pytest
import unittest
from json import dumps

from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, UserFactory, AuthUserFactory, DraftRegistrationFactory

from github3.repos.branch import Branch

from framework.exceptions import HTTPError
from framework.auth import Auth

from addons.base.tests.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from addons.gitlab import utils
from addons.gitlab.api import GitLabClient
from addons.gitlab.serializer import GitLabSerializer
from addons.gitlab.utils import check_permissions
from addons.gitlab.tests.utils import create_mock_gitlab, GitLabAddonTestCase
from addons.gitlab.tests.factories import GitLabAccountFactory

pytestmark = pytest.mark.django_db

class TestGitLabAuthViews(GitLabAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    @mock.patch(
        'addons.gitlab.models.UserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super().test_delete_external_account()

    def test_oauth_start(self):
        pass

    def test_oauth_finish(self):
        pass


class TestGitLabConfigViews(GitLabAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = None
    Serializer = GitLabSerializer
    client = GitLabClient

    ## Overrides ##

    def setUp(self):
        super().setUp()
        self.mock_api_user = mock.patch('addons.gitlab.api.GitLabClient.user')
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super().tearDown()

    def test_folder_list(self):
        # GH only lists root folder (repos), this test is superfluous
        pass

    @mock.patch('addons.gitlab.models.NodeSettings.add_hook')
    @mock.patch('addons.gitlab.views.GitLabClient.repo')
    def test_set_config(self, mock_repo, mock_add_hook):
        # GH selects repos, not folders, so this needs to be overriden
        mock_repo.return_value = 'repo_name'
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_set_config')
        res = self.app.post(url, json={
            'gitlab_user': 'octocat',
            'gitlab_repo': 'repo_name',
            'gitlab_repo_id': '123',
        }, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        self.project.reload()
        assert self.project.logs.latest().action == f'{self.ADDON_SHORT_NAME}_repo_linked'
        mock_add_hook.assert_called_once_with(save=False)


# TODO: Test remaining CRUD methods
# TODO: Test exception handling
class TestCRUD(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.gitlab = create_mock_gitlab(user='fred', private=False)
        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('gitlab', auth=self.consolidated_auth)
        self.project.creator.add_addon('gitlab')
        self.node_settings = self.project.get_addon('gitlab')
        self.node_settings.user_settings = self.project.creator.get_addon('gitlab')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = self.gitlab.repo.return_value.owner.login
        self.node_settings.repo = self.gitlab.repo.return_value.name
        self.node_settings.save()


class TestGitLabViews(OsfTestCase):

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
        self.project.save()
        self.project.add_addon('gitlab', auth=self.consolidated_auth)
        self.project.creator.add_addon('gitlab')
        self.project.creator.external_accounts.add(GitLabAccountFactory())
        self.project.creator.save()

        self.gitlab = create_mock_gitlab(user='fred', private=False)

        self.node_settings = self.project.get_addon('gitlab')
        self.node_settings.user_settings = self.project.creator.get_addon('gitlab')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = 'fred'
        self.node_settings.repo = 'mock-repo'
        self.node_settings.repo_id = 1748448
        self.node_settings.save()

    def _get_sha_for_branch(self, branch=None, mock_branches=None):
        gitlab_mock = self.gitlab
        if mock_branches is None:
            mock_branches = gitlab_mock.branches
        if branch is None:  # Get default branch name
            branch = self.gitlab.repo.default_branch
        for each in mock_branches:
            if each.name == branch:
                branch_sha = each.commit['id']
        return branch_sha

    # Tests for _get_refs
    @mock.patch('addons.gitlab.api.GitLabClient.branches')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_get_refs_defaults(self, mock_repo, mock_branches):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo
        mock_branches.return_value = gitlab_mock.branches.return_value
        branch, sha, branches = utils.get_refs(self.node_settings)
        assert branch == gitlab_mock.repo.default_branch
        assert sha == branches[0].commit['id']  # Get refs for default branch
        assert branches == gitlab_mock.branches.return_value

    @mock.patch('addons.gitlab.api.GitLabClient.branches')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_get_refs_branch(self, mock_repo, mock_branches):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo.return_value
        mock_branches.return_value = gitlab_mock.branches.return_value
        branch, sha, branches = utils.get_refs(self.node_settings, 'master')
        assert branch == 'master'
        assert sha == branches[0].commit['id']
        assert branches == gitlab_mock.branches.return_value

    def test_before_fork(self):
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert len(res.json['prompts']) == 1

    @mock.patch('addons.gitlab.models.UserSettings.has_auth')
    def test_before_register(self, mock_has_auth):
        mock_has_auth.return_value = True
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth,follow_redirects=True)
        assert 'GitLab' in res.json['prompts'][1]

    def test_get_refs_sha_no_branch(self):
        with pytest.raises(HTTPError):
            utils.get_refs(self.node_settings, sha='12345')

    # Tests for _check_permissions
    # make a user with no authorization; make sure check_permissions returns false
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_permissions_no_auth(self, mock_repo):
        gitlab_mock = self.gitlab
        # project is set to private right now
        mock_repository = mock.Mock(**{
            'user': 'fred',
            'repo': 'mock-repo',
            'permissions': {
                'project_access': {'access_level': 20, 'notification_level': 3}
            },
        })
        mock_repo.attributes.return_value = mock_repository


        connection = gitlab_mock
        non_authenticated_user = UserFactory()
        non_authenticated_auth = Auth(user=non_authenticated_user)
        branch = 'master'
        assert not check_permissions(self.node_settings, non_authenticated_auth, connection, branch, repo=mock_repository)

    # make a repository that doesn't allow push access for this user;
    # make sure check_permissions returns false
    @mock.patch('addons.gitlab.models.UserSettings.has_auth')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_permissions_no_access(self, mock_repo, mock_has_auth):
        gitlab_mock = self.gitlab
        mock_has_auth.return_value = True
        connection = gitlab_mock
        branch = 'master'
        mock_repository = mock.Mock(**{
            'user': 'fred',
            'repo': 'mock-repo',
            'permissions': {
                'project_access': {'access_level': 20, 'notification_level': 3}
            },
        })
        mock_repo.attributes.return_value = mock_repository
        assert not check_permissions(self.node_settings, self.consolidated_auth, connection, branch, repo=mock_repository)

    # make a branch with a different commit than the commit being passed into check_permissions
    @mock.patch('addons.gitlab.models.UserSettings.has_auth')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_permissions_not_head(self, mock_repo, mock_has_auth):
        gitlab_mock = self.gitlab
        mock_has_auth.return_value = True
        connection = gitlab_mock
        mock_branch = mock.Mock(**{
            'commit': {'id': '67890'}
        })
        mock_repository = mock.Mock(**{
            'user': 'fred',
            'repo': 'mock-repo',
            'permissions': {
                'project_access': {'access_level': 20, 'notification_level': 3}
            },
        })
        mock_repo.attributes.return_value = mock_repository
        connection.branches.return_value = mock_branch
        sha = '12345'
        assert not check_permissions(self.node_settings, self.consolidated_auth, connection, mock_branch, sha=sha, repo=mock_repository)

    # make sure permissions are not granted for editing a registration
    @mock.patch('addons.gitlab.models.UserSettings.has_auth')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_permissions(self, mock_repo, mock_has_auth):
        gitlab_mock = self.gitlab
        mock_has_auth.return_value = True
        connection = gitlab_mock
        mock_repository = mock.Mock(**{
            'user': 'fred',
            'repo': 'mock-repo',
            'permissions': {
                'project_access': {'access_level': 20, 'notification_level': 3}
            },
        })
        mock_repo.attributes.return_value = mock_repository
        with mock.patch('osf.models.node.AbstractNode.is_registration', new_callable=mock.PropertyMock) as mock_is_reg:
            mock_is_reg.return_value = True
            assert not check_permissions(self.node_settings, self.consolidated_auth, connection, 'master', repo=mock_repository)

    def check_hook_urls(self, urls, node, path, sha):
        url = node.web_url_for('addon_view_or_download_file', path=path, provider='gitlab')
        expected_urls = {
            'view': f'{url}?branch={sha}',
            'download': f'{url}?action=download&branch={sha}'
        }

        assert urls['view'] == expected_urls['view']
        assert urls['download'] == expected_urls['download']

    @mock.patch('addons.gitlab.views.verify_hook_signature')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_hook_callback_add_file_not_thro_osf(self, mock_repo, mock_verify):
        gitlab_mock = self.gitlab
        gitlab_mock.repo = mock_repo
        url = f'/api/v1/project/{self.project._id}/gitlab/hook/'
        timestamp = str(datetime.datetime.utcnow())
        self.app.post(
            url,
            json={
                'test': True,
                'commits': [{
                    'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                    'distinct': True,
                    'message': 'foo',
                    'timestamp': timestamp,
                    'url': 'https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
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
        assert self.project.logs.latest().action == 'gitlab_file_added'
        urls = self.project.logs.latest().params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_modify_file_not_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/gitlab/hook/'
        timestamp = str(datetime.datetime.utcnow())
        self.app.post(
            url,
            json={'test': True,
                 'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                              'distinct': True,
                              'message': ' foo',
                              'timestamp': timestamp,
                              'url': 'https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                              'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                              'committer': {'name': 'Testor', 'email': 'test@osf.io',
                                            'username': 'tester'},
                              'added': [], 'removed':[], 'modified':['PRJWN3TV']}]},
            content_type='application/json', follow_redirects=True)
        self.project.reload()
        assert self.project.logs.latest().action == 'gitlab_file_updated'
        urls = self.project.logs.latest().params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_remove_file_not_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/gitlab/hook/'
        timestamp = str(datetime.datetime.utcnow())
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'foo',
                          'timestamp': timestamp,
                          'url': 'https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed': ['PRJWN3TV'], 'modified':[]}]},
            content_type='application/json', follow_redirects=True)
        self.project.reload()
        assert self.project.logs.latest().action == 'gitlab_file_removed'
        urls = self.project.logs.latest().params['urls']
        assert urls == {}

    @mock.patch('addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_add_file_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/gitlab/hook/'
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Added via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': ['PRJWN3TV'], 'removed':[], 'modified':[]}]},
            content_type='application/json', follow_redirects=True)
        self.project.reload()
        assert self.project.logs.latest().action != 'gitlab_file_added'

    @mock.patch('addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_modify_file_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/gitlab/hook/'
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Updated via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed':[], 'modified':['PRJWN3TV']}]},
            content_type='application/json', follow_redirects=True)
        self.project.reload()
        assert self.project.logs.latest().action != 'gitlab_file_updated'

    @mock.patch('addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_remove_file_thro_osf(self, mock_verify):
        url = f'/api/v1/project/{self.project._id}/gitlab/hook/'
        self.app.post(
            url,
            json={'test': True,
             'commits': [{'id': 'b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'distinct': True,
                          'message': 'Deleted via the Open Science Framework',
                          'timestamp': '2014-01-08T14:15:51-08:00',
                          'url': 'https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
                          'author': {'name': 'Illidan', 'email': 'njqpw@osf.io'},
                          'committer': {'name': 'Testor', 'email': 'test@osf.io', 'username': 'tester'},
                          'added': [], 'removed':['PRJWN3TV'], 'modified':[]}]},
            content_type='application/json', follow_redirects=True)
        self.project.reload()
        assert self.project.logs.latest().action != 'gitlab_file_removed'


class TestRegistrationsWithGitLab(OsfTestCase):

    def setUp(self):

        super().setUp()
        self.project = ProjectFactory.build()
        self.project.save()
        self.consolidated_auth = Auth(user=self.project.creator)

        self.project.add_addon('gitlab', auth=self.consolidated_auth)
        self.project.creator.add_addon('gitlab')
        self.node_settings = self.project.get_addon('gitlab')
        self.user_settings = self.project.creator.get_addon('gitlab')
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


class TestGitLabSettings(OsfTestCase):

    def setUp(self):

        super().setUp()
        self.gitlab = create_mock_gitlab(user='fred', private=False)
        self.project = ProjectFactory()
        self.auth = self.project.creator.auth
        self.consolidated_auth = Auth(user=self.project.creator)

        self.project.add_addon('gitlab', auth=self.consolidated_auth)
        self.project.creator.add_addon('gitlab')
        self.node_settings = self.project.get_addon('gitlab')
        self.user_settings = self.project.creator.get_addon('gitlab')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.repo_id = 'sheer-heart-attack'
        self.node_settings.save()

    @mock.patch('addons.gitlab.models.NodeSettings.add_hook')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_link_repo(self, mock_repo, mock_add_hook):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo.return_value

        url = self.project.api_url + 'gitlab/settings/'
        self.app.post(
            url,
            json={
                'gitlab_user': 'queen',
                'gitlab_repo': 'night at the opera',
                'gitlab_repo_id': 'abc',
            },
            auth=self.auth
        , follow_redirects=True)

        self.project.reload()
        self.node_settings.reload()

        assert self.node_settings.user == 'queen'
        assert self.node_settings.repo == 'night at the opera'
        assert self.project.logs.latest().action == 'gitlab_repo_linked'
        mock_add_hook.assert_called_once_with(save=False)

    @mock.patch('addons.gitlab.models.NodeSettings.add_hook')
    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_link_repo_no_change(self, mock_repo, mock_add_hook):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo.return_value

        log_count = self.project.logs.count()

        url = self.project.api_url + 'gitlab/settings/'
        self.app.post(
            url,
            json={
                'gitlab_user': self.node_settings.user,
                'gitlab_repo': self.node_settings.repo,
                'gitlab_repo_id': self.node_settings.repo_id,
            },
            auth=self.auth
        , follow_redirects=True)

        self.project.reload()
        self.node_settings.reload()

        assert self.project.logs.count() == log_count
        assert not mock_add_hook.called

    @mock.patch('addons.gitlab.api.GitLabClient.repo')
    def test_link_repo_non_existent(self, mock_repo):

        mock_repo.return_value = None

        url = self.project.api_url + 'gitlab/settings/'
        res = self.app.post(
            url,
            json={
                'gitlab_user': 'queen',
                'gitlab_repo': 'night at the opera',
            },
            auth=self.auth,
            follow_redirects=True
        )

        assert res.status_code == 400

    @mock.patch('addons.gitlab.api.GitLabClient.branches')
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

        url = registration.api_url + 'gitlab/settings/'
        res = self.app.post(
            url,
            json={
                'gitlab_user': 'queen',
                'gitlab_repo': 'night at the opera',
            },
            auth=self.auth,
            follow_redirects=True
        )

        assert res.status_code == 400

    @mock.patch('addons.gitlab.models.NodeSettings.delete_hook')
    def test_deauthorize(self, mock_delete_hook):

        url = self.project.api_url + 'gitlab/user_auth/'

        self.app.delete(url, auth=self.auth, follow_redirects=True)

        self.project.reload()
        self.node_settings.reload()
        assert self.node_settings.user is None
        assert self.node_settings.repo is None
        assert self.node_settings.user_settings is None

        assert self.project.logs.latest().action == 'gitlab_node_deauthorized'


if __name__ == '__main__':
    unittest.main()
