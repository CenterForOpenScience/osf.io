# -*- coding: utf-8 -*-

import mock
import unittest

from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, AuthUserFactory

from github3.repos.branch import Branch

from framework.exceptions import HTTPError
from framework.auth import Auth

from website.util import api_url_for
from website.addons.github import views, utils
from website.addons.github.utils import check_permissions
from website.addons.github.tests.utils import create_mock_github
from website.addons.github.tests.factories import (
    GitHubAccountFactory,
    GitHubUserSettingsFactory,
    ExternalAccountFactory,
)
from website.addons.github import model
from website.addons.github.serializer import GitHubSerializer

from faker import Faker
fake = Faker()

class MockGithubRepo(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

class MockGithubOwner(object):

    def __init__(self, **kwargs):
        self.login = fake.domain_word()



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
        self.account = GitHubAccountFactory()
        self.user = AuthUserFactory(external_accounts=[self.account])
        self.user_settings = self.user.get_or_add_addon('github')
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('github', Auth(self.user))

        self.node_settings = self.project.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.set_auth(external_account=self.account, user=self.user)
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()
        self.user_settings.save()
        self.app.authenticate(*self.user.auth)
        self.github = create_mock_github(user='fred', private=False)

    def test_serialize_settings_authorizer(self):

        res = self.app.get(
            self.project.api_url_for('github_get_config'),
            auth=self.user.auth,
        )

        result = res.json['result']
        assert_true(result['nodeHasAuth'])
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])
        assert_equal(result['ownerName'], self.user.fullname)
        assert_true(result['urls']['auth'])
        assert_true(result['urls']['config'])
        assert_true(result['urls']['deauthorize'])
        assert_true(result['urls']['importAuth'])
        assert_true(result['urls']['settings'])

    def test_serialize_settings_non_authorizer(self):
        non_authorizing_user = AuthUserFactory()
        self.project.add_contributor(non_authorizing_user, save=True)

        res = self.app.get(
            self.project.api_url_for('github_get_config'),
            auth=non_authorizing_user.auth,
        )

        result = res.json['result']
        assert_true(result['nodeHasAuth'])
        assert_false(result['userHasAuth'])
        assert_false(result['userIsOwner'])
        assert_equal(result['ownerName'], self.user.fullname)
        assert_true(result['urls']['auth'])
        assert_true(result['urls']['config'])
        assert_true(result['urls']['deauthorize'])
        assert_true(result['urls']['importAuth'])
        assert_true(result['urls']['settings'])

    def test_set_auth(self):

        res = self.app.put_json(
            self.project.api_url_for('github_add_user_auth'),
            {
                'external_account_id': self.account._id,
            },
            auth=self.user.auth,
        )

        assert_equal(
            res.status_code,
            200
        )

        assert_true(res.json['result']['userHasAuth'])

        assert_equal(
            self.node_settings.user_settings,
            self.user_settings
        )
        assert_equal(
            self.node_settings.external_account,
            self.account
        )

    def test_remove_user_auth(self):
        self.node_settings.set_auth(self.account, self.user)

        res = self.app.delete_json(
            self.project.api_url_for('github_remove_user_auth'),
            {
                'external_account_id': self.account._id,
            },
            auth=self.user.auth,
        )

        assert_equal(
            res.status_code,
            200
        )

        self.node_settings.reload()

        assert_is_none(self.node_settings.user_settings)
        assert_is_none(self.node_settings.external_account)


    @mock.patch('website.addons.github.model.GitHubNodeSettings.add_hook')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_github_set_config(self, mock_repo, mock_add_hook):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value

        res = self.app.post_json(
            self.project.api_url_for('github_set_config'),
            {
                'external_account_id': self.account._id,
                'github_repo': 'fakeuser / fakerepo',
            },
            auth=self.user.auth,

        )

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.node_settings.user, 'fakeuser')
        assert_equal(self.node_settings.repo, 'fakerepo')
        assert_equal(self.project.logs[-1].action, 'github_repo_linked')
        mock_add_hook.assert_called_once()

    @mock.patch('website.addons.github.model.GitHubNodeSettings.add_hook')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_github_set_config_no_change(self, mock_repo, mock_add_hook):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value

        log_count = len(self.project.logs)

        res = self.app.post_json(
            self.project.api_url_for('github_set_config'),
            {
                'external_account_id': self.account._id,
                'github_repo': 'Queen / Sheer-Heart-Attack',
            },
            auth=self.user.auth,

        )

        self.project.reload()
        self.node_settings.reload()

        assert_equal(len(self.project.logs), log_count)
        assert_false(mock_add_hook.called)

    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_github_set_change_non_existant(self, mock_repo):

        mock_repo.return_value = None

        res = self.app.post_json(
            self.project.api_url_for('github_set_config'),
            {
                'external_account_id': self.account._id,
                'github_repo': 'fakeuser / fakerepo',
            },
            auth=self.user.auth,
            expect_errors=True

        )

        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.github.api.GitHub.branches')
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
            None, Auth(self.user), '', ''
        )

        url = registration.api_url + 'github/settings/'
        res = self.app.post_json(
            url,
            {
                'github_repo': 'queen / night at the opera',
            },
            auth=self.user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 400)



    @mock.patch('website.addons.github.api.GitHub.repos')
    @mock.patch('website.addons.github.api.GitHub.my_org_repos')
    def test_github_repo_list(self, mock_my_org_repos, mock_repos):

        fake_repos = [
            MockGithubRepo(name=fake.domain_word(), owner=MockGithubOwner())
            for i in range(10)
        ]
        mock_repos.return_value = fake_repos
        url = self.node_settings.owner.api_url_for('github_repo_list')
        ret = self.app.get(url, auth=self.user.auth)
        assert_equals(ret.json['repo_names'], [repo.name for repo in fake_repos])
        assert_equals(ret.json['user_names'], [repo.owner.login for repo in fake_repos])

    @mock.patch('website.addons.github.api.GitHub.create_repo')
    @mock.patch('website.addons.github.api.GitHub.repos')
    @mock.patch('website.addons.github.api.GitHub.my_org_repos')
    def test_create_repo(self, mock_my_org_repos, mock_repos, mock_repo):
        fake_name = fake.domain_word()
        mock_repo.return_value = MockGithubRepo(name=fake_name, owner=MockGithubOwner())

        fake_repos = [
            MockGithubRepo(name=fake.domain_word(), owner=MockGithubOwner())
            # for i in range(10)
        ]
        mock_repos.return_value = fake_repos

        ret = self.app.post_json(
            self.project.api_url_for('github_create_repo'),
            {
                'external_account_id': self.account._id,
                'repo_name': fake_name,
            },
            auth=self.user.auth,

        )
        assert_equals(ret.json['repo_names'], [repo.name for repo in fake_repos])

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
    @mock.patch('website.addons.github.api.GitHub.branches')
    @mock.patch('website.addons.github.api.GitHub.repo')
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

    @mock.patch('website.addons.github.api.GitHub.branches')
    @mock.patch('website.addons.github.api.GitHub.repo')
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

    def test_before_remove_contributor_authenticator(self):
        url = self.project.api_url + 'beforeremovecontributors/'
        res = self.app.post_json(
            url,
            {'id': self.project.creator._id},
            auth=self.user.auth,
        ).maybe_follow()
        # One prompt for transferring auth, one for removing self
        assert_equal(len(res.json['prompts']), 2)

    def test_before_remove_contributor_not_authenticator(self):
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.user),
        )
        url = self.project.api_url + 'beforeremovecontributors/'
        res = self.app.post_json(
            url,
            {'id': self.non_authenticator._id},
            auth=self.user.auth,
        ).maybe_follow()
        assert_equal(len(res.json['prompts']), 0)

    def test_before_fork(self):
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(len(res.json['prompts']), 1)

    @mock.patch('website.addons.github.model.GitHubUserSettings.has_auth')
    def test_before_register(self, mock_has_auth):
        mock_has_auth.return_value = True
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(len(res.json['prompts']), 1)

    def test_get_refs_sha_no_branch(self):
        with assert_raises(HTTPError):
            utils.get_refs(self.node_settings, sha='12345')

    def test_get_refs_registered_missing_branch(self):
        github_mock = self.github
        self.node_settings.registration_data = {
            'branches': [
                branch.to_json()
                for branch in github_mock.branches.return_value
            ]
        }
        self.node_settings.owner.is_registration = True
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
    @mock.patch('website.addons.github.model.GitHubUserSettings.has_auth')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_permissions_no_access(self, mock_repo, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        branch = 'master'
        mock_repository = mock.NonCallableMock()
        mock_repository.user = 'fred'
        mock_repository.repo = 'mock-repo'
        mock_repository.to_json.return_value = {
            'user': 'fred',
            'repo': 'mock-repo',
            'permissions': {
                'push': False,  # this is key
            },
        }
        mock_repo.return_value = mock_repository
        assert_false(check_permissions(self.node_settings, Auth(self.user), connection, branch, repo=mock_repository))

    # make a branch with a different commit than the commit being passed into check_permissions
    @mock.patch('website.addons.github.model.GitHubUserSettings.has_auth')
    def test_permissions_not_head(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        mock_branch = mock.NonCallableMock()
        mock_branch.commit.sha = '67890'
        sha = '12345'
        assert_false(check_permissions(self.node_settings, Auth(self.user), connection, mock_branch, sha=sha))

    # make sure permissions are not granted for editing a registration
    @mock.patch('website.addons.github.model.GitHubUserSettings.has_auth')
    def test_permissions(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        self.node_settings.owner.is_registration = True
        assert_false(check_permissions(self.node_settings, Auth(self.user), connection, 'master'))

    def check_hook_urls(self, urls, node, path, sha):
        url = node.web_url_for('addon_view_or_download_file', path=path, provider='github')
        expected_urls = {
            'view': '{0}?ref={1}'.format(url, sha),
            'download': '{0}?action=download&ref={1}'.format(url, sha)
        }

        assert_equal(urls['view'], expected_urls['view'])
        assert_equal(urls['download'], expected_urls['download'])

    @mock.patch('website.addons.github.views.hooks.utils.verify_hook_signature')
    def test_hook_callback_add_file_not_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {
                "test": True,
                "commits": [{
                    "id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                    "distinct": True,
                    "message": "foo",
                    "timestamp": "2014-01-08T14:15:51-08:00",
                    "url": "https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                    "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                    "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                    "added": ["PRJWN3TV"],
                    "removed": [],
                    "modified": [],
                }]
            },
            content_type="application/json",
        ).maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "github_file_added")
        urls = self.project.logs[-1].params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('website.addons.github.views.hooks.utils.verify_hook_signature')
    def test_hook_callback_modify_file_not_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
                 "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct": True,
                              "message": " foo",
                              "timestamp": "2014-01-08T14:15:51-08:00",
                              "url": "https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                              "committer": {"name": "Testor", "email": "test@osf.io",
                                            "username": "tester"},
                              "added": [], "removed":[], "modified":["PRJWN3TV"]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "github_file_updated")
        urls = self.project.logs[-1].params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('website.addons.github.views.hooks.utils.verify_hook_signature')
    def test_hook_callback_remove_file_not_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "foo",
                          "timestamp": "2014-01-08T14:15:51-08:00",
                          "url": "https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": [], "removed": ["PRJWN3TV"], "modified":[]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "github_file_removed")
        urls = self.project.logs[-1].params['urls']
        assert_equal(urls, {})

    @mock.patch('website.addons.github.views.hooks.utils.verify_hook_signature')
    def test_hook_callback_add_file_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "Added via the Open Science Framework",
                          "timestamp": "2014-01-08T14:15:51-08:00",
                          "url": "https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": ["PRJWN3TV"], "removed":[], "modified":[]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "github_file_added")

    @mock.patch('website.addons.github.views.hooks.utils.verify_hook_signature')
    def test_hook_callback_modify_file_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "Updated via the Open Science Framework",
                          "timestamp": "2014-01-08T14:15:51-08:00",
                          "url": "https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": [], "removed":[], "modified":["PRJWN3TV"]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "github_file_updated")

    @mock.patch('website.addons.github.views.hooks.utils.verify_hook_signature')
    def test_hook_callback_remove_file_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "Deleted via the Open Science Framework",
                          "timestamp": "2014-01-08T14:15:51-08:00",
                          "url": "https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": [], "removed":["PRJWN3TV"], "modified":[]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "github_file_removed")


class TestRegistrationsWithGithub(OsfTestCase):

    def setUp(self):

        super(TestRegistrationsWithGithub, self).setUp()
        self.project = ProjectFactory.build()
        self.project.save()
        self.consolidated_auth = Auth(user=self.project.creator)

        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')
        self.node_settings = self.project.get_addon('github')
        self.user_settings = self.project.creator.get_addon('github')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()



if __name__ == '__main__':
    unittest.main()
