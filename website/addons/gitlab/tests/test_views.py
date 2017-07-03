# -*- coding: utf-8 -*-
import httplib as http

import mock
import datetime
import unittest

from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase, get_default_metaschema
from tests.factories import ProjectFactory, UserFactory, AuthUserFactory

from github3.repos.branch import Branch

from framework.exceptions import HTTPError
from framework.auth import Auth

from website.util import api_url_for
from website.addons.base.testing.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from website.addons.gitlab import views, utils
from website.addons.gitlab.api import GitLabClient
from website.addons.gitlab.model import GitLabProvider
from website.addons.gitlab.serializer import GitLabSerializer
from website.addons.gitlab.utils import check_permissions
from website.addons.gitlab.tests.utils import create_mock_gitlab, GitLabAddonTestCase
from website.addons.gitlab.tests.factories import GitLabAccountFactory


class TestGitLabAuthViews(GitLabAddonTestCase, OAuthAddonAuthViewsTestCaseMixin):
    
    @mock.patch(
        'website.addons.gitlab.model.GitLabUserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super(TestGitLabAuthViews, self).test_delete_external_account()


class TestGitLabConfigViews(GitLabAddonTestCase, OAuthAddonConfigViewsTestCaseMixin):
    folder = None
    Serializer = GitLabSerializer
    client = GitLabClient

    ## Overrides ##

    def setUp(self):
        super(TestGitLabConfigViews, self).setUp()
        self.mock_api_user = mock.patch("website.addons.gitlab.api.GitLabClient.user")
        self.mock_api_user.return_value = mock.Mock()
        self.mock_api_user.start()

    def tearDown(self):
        self.mock_api_user.stop()
        super(TestGitLabConfigViews, self).tearDown()

    def test_folder_list(self):
        # GH only lists root folder (repos), this test is superfluous
        pass

    @mock.patch('website.addons.gitlab.model.GitLabNodeSettings.add_hook')
    @mock.patch('website.addons.gitlab.views.GitLabClient.repo')
    def test_set_config(self, mock_repo, mock_add_hook):
        # GH selects repos, not folders, so this needs to be overriden
        mock_repo.return_value = 'repo_name'
        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.post_json(url, {
            'gitlab_user': 'octocat',
            'gitlab_repo': 'repo_name',
        }, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.project.reload()
        assert_equal(
            self.project.logs[-1].action,
            '{0}_repo_linked'.format(self.ADDON_SHORT_NAME)
        )
        mock_add_hook.assert_called_once()


# TODO: Test remaining CRUD methods
# TODO: Test exception handling
class TestCRUD(OsfTestCase):

    def setUp(self):
        super(TestCRUD, self).setUp()
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
        super(TestGitLabViews, self).setUp()
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
        self.project.creator.external_accounts.append(GitLabAccountFactory())
        self.project.creator.save()

        self.gitlab = create_mock_gitlab(user='fred', private=False)

        self.node_settings = self.project.get_addon('gitlab')
        self.node_settings.user_settings = self.project.creator.get_addon('gitlab')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = self.gitlab.repo.return_value.owner.login
        self.node_settings.repo = self.gitlab.repo.return_value.name
        self.node_settings.save()

    def _get_sha_for_branch(self, branch=None, mock_branches=None):
        gitlab_mock = self.gitlab
        if mock_branches is None:
            mock_branches = gitlab_mock.branches
        if branch is None:  # Get default branch name
            branch = self.gitlab.repo.return_value.default_branch
        for each in mock_branches.return_value:
            if each.name == branch:
                branch_sha = each.commit.sha
        return branch_sha

    # Tests for _get_refs
    @mock.patch('website.addons.gitlab.api.GitLabClient.branches')
    @mock.patch('website.addons.gitlab.api.GitLabClient.repo')
    def test_get_refs_defaults(self, mock_repo, mock_branches):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo.return_value
        mock_branches.return_value = gitlab_mock.branches.return_value
        branch, sha, branches = utils.get_refs(self.node_settings)
        assert_equal(
            branch,
            gitlab_mock.repo.return_value.default_branch
        )
        assert_equal(sha, self._get_sha_for_branch(branch=None))  # Get refs for default branch
        assert_equal(
            branches,
            gitlab_mock.branches.return_value
        )

    @mock.patch('website.addons.gitlab.api.GitLabClient.branches')
    @mock.patch('website.addons.gitlab.api.GitLabClient.repo')
    def test_get_refs_branch(self, mock_repo, mock_branches):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo.return_value
        mock_branches.return_value = gitlab_mock.branches.return_value
        branch, sha, branches = utils.get_refs(self.node_settings, 'master')
        assert_equal(branch, 'master')
        branch_sha = self._get_sha_for_branch('master')
        assert_equal(sha, branch_sha)
        assert_equal(
            branches,
            gitlab_mock.branches.return_value
        )

    def test_before_fork(self):
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(len(res.json['prompts']), 1)

    @mock.patch('website.addons.gitlab.model.GitLabUserSettings.has_auth')
    def test_before_register(self, mock_has_auth):
        mock_has_auth.return_value = True
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_true('GitLab' in res.json['prompts'][1])
        
    def test_get_refs_sha_no_branch(self):
        with assert_raises(HTTPError):
            utils.get_refs(self.node_settings, sha='12345')

    def test_get_refs_registered_missing_branch(self):
        gitlab_mock = self.gitlab
        self.node_settings.registration_data = {
            'branches': [
                branch.to_json()
                for branch in gitlab_mock.branches.return_value
            ]
        }
        self.node_settings.owner.is_registration = True
        with assert_raises(HTTPError):
            utils.get_refs(self.node_settings, branch='nothere')

    # Tests for _check_permissions
    # make a user with no authorization; make sure check_permissions returns false
    def test_permissions_no_auth(self):
        gitlab_mock = self.gitlab
        # project is set to private right now
        connection = gitlab_mock
        non_authenticated_user = UserFactory()
        non_authenticated_auth = Auth(user=non_authenticated_user)
        branch = 'master'
        assert_false(check_permissions(self.node_settings, non_authenticated_auth, connection, branch))

    # make a repository that doesn't allow push access for this user;
    # make sure check_permissions returns false
    @mock.patch('website.addons.gitlab.model.GitLabUserSettings.has_auth')
    @mock.patch('website.addons.gitlab.api.GitLabClient.repo')
    def test_permissions_no_access(self, mock_repo, mock_has_auth):
        gitlab_mock = self.gitlab
        mock_has_auth.return_value = True
        connection = gitlab_mock
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
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, branch, repo=mock_repository))

    # make a branch with a different commit than the commit being passed into check_permissions
    @mock.patch('website.addons.gitlab.model.GitLabUserSettings.has_auth')
    def test_permissions_not_head(self, mock_has_auth):
        gitlab_mock = self.gitlab
        mock_has_auth.return_value = True
        connection = gitlab_mock
        mock_branch = mock.NonCallableMock()
        mock_branch.commit.sha = '67890'
        sha = '12345'
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, mock_branch, sha=sha))

    # make sure permissions are not granted for editing a registration
    @mock.patch('website.addons.gitlab.model.GitLabUserSettings.has_auth')
    def test_permissions(self, mock_has_auth):
        gitlab_mock = self.gitlab
        mock_has_auth.return_value = True
        connection = gitlab_mock
        self.node_settings.owner.is_registration = True
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, 'master'))

    def check_hook_urls(self, urls, node, path, sha):
        url = node.web_url_for('addon_view_or_download_file', path=path, provider='gitlab')
        expected_urls = {
            'view': '{0}?ref={1}'.format(url, sha),
            'download': '{0}?action=download&ref={1}'.format(url, sha)
        }

        assert_equal(urls['view'], expected_urls['view'])
        assert_equal(urls['download'], expected_urls['download'])

    @mock.patch('website.addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_add_file_not_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/gitlab/hook/".format(self.project._id)
        timestamp = str(datetime.datetime.utcnow())
        self.app.post_json(
            url,
            {
                "test": True,
                "commits": [{
                    "id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                    "distinct": True,
                    "message": "foo",
                    "timestamp": timestamp,
                    "url": "https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
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
        assert_equal(self.project.logs[-1].action, "gitlab_file_added")
        urls = self.project.logs[-1].params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('website.addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_modify_file_not_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/gitlab/hook/".format(self.project._id)
        timestamp = str(datetime.datetime.utcnow())
        self.app.post_json(
            url,
            {"test": True,
                 "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct": True,
                              "message": " foo",
                              "timestamp": timestamp,
                              "url": "https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                              "committer": {"name": "Testor", "email": "test@osf.io",
                                            "username": "tester"},
                              "added": [], "removed":[], "modified":["PRJWN3TV"]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "gitlab_file_updated")
        urls = self.project.logs[-1].params['urls']
        self.check_hook_urls(
            urls,
            self.project,
            path='PRJWN3TV',
            sha='b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce',
        )

    @mock.patch('website.addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_remove_file_not_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/gitlab/hook/".format(self.project._id)
        timestamp = str(datetime.datetime.utcnow())
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "foo",
                          "timestamp": timestamp,
                          "url": "https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": [], "removed": ["PRJWN3TV"], "modified":[]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "gitlab_file_removed")
        urls = self.project.logs[-1].params['urls']
        assert_equal(urls, {})

    @mock.patch('website.addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_add_file_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/gitlab/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "Added via the Open Science Framework",
                          "timestamp": "2014-01-08T14:15:51-08:00",
                          "url": "https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": ["PRJWN3TV"], "removed":[], "modified":[]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "gitlab_file_added")

    @mock.patch('website.addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_modify_file_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/gitlab/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "Updated via the Open Science Framework",
                          "timestamp": "2014-01-08T14:15:51-08:00",
                          "url": "https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": [], "removed":[], "modified":["PRJWN3TV"]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "gitlab_file_updated")

    @mock.patch('website.addons.gitlab.views.verify_hook_signature')
    def test_hook_callback_remove_file_thro_osf(self, mock_verify):
        url = "/api/v1/project/{0}/gitlab/hook/".format(self.project._id)
        self.app.post_json(
            url,
            {"test": True,
             "commits": [{"id": "b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "distinct": True,
                          "message": "Deleted via the Open Science Framework",
                          "timestamp": "2014-01-08T14:15:51-08:00",
                          "url": "https://gitlab.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                          "author": {"name": "Illidan", "email": "njqpw@osf.io"},
                          "committer": {"name": "Testor", "email": "test@osf.io", "username": "tester"},
                          "added": [], "removed":["PRJWN3TV"], "modified":[]}]},
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "gitlab_file_removed")


class TestRegistrationsWithGitLab(OsfTestCase):

    def setUp(self):

        super(TestRegistrationsWithGitLab, self).setUp()
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


class TestGitLabSettings(OsfTestCase):

    def setUp(self):

        super(TestGitLabSettings, self).setUp()
        self.gitlab = create_mock_gitlab(user='fred', private=False)
        self.project = ProjectFactory.build()
        self.project.save()
        self.auth = self.project.creator.auth
        self.consolidated_auth = Auth(user=self.project.creator)

        self.project.add_addon('gitlab', auth=self.consolidated_auth)
        self.project.creator.add_addon('gitlab')
        self.node_settings = self.project.get_addon('gitlab')
        self.user_settings = self.project.creator.get_addon('gitlab')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.user = 'Queen'
        self.node_settings.repo = 'Sheer-Heart-Attack'
        self.node_settings.save()

    @mock.patch('website.addons.gitlab.model.GitLabNodeSettings.add_hook')
    @mock.patch('website.addons.gitlab.api.GitLabClient.repo')
    def test_link_repo(self, mock_repo, mock_add_hook):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo.return_value

        url = self.project.api_url + 'gitlab/settings/'
        self.app.post_json(
            url,
            {
                'gitlab_user': 'queen',
                'gitlab_repo': 'night at the opera',
            },
            auth=self.auth
        ).maybe_follow()

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.node_settings.user, 'queen')
        assert_equal(self.node_settings.repo, 'night at the opera')
        assert_equal(self.project.logs[-1].action, 'gitlab_repo_linked')
        mock_add_hook.assert_called_once()

    @mock.patch('website.addons.gitlab.model.GitLabNodeSettings.add_hook')
    @mock.patch('website.addons.gitlab.api.GitLabClient.repo')
    def test_link_repo_no_change(self, mock_repo, mock_add_hook):
        gitlab_mock = self.gitlab
        mock_repo.return_value = gitlab_mock.repo.return_value

        log_count = len(self.project.logs)

        url = self.project.api_url + 'gitlab/settings/'
        self.app.post_json(
            url,
            {
                'gitlab_user': 'Queen',
                'gitlab_repo': 'Sheer-Heart-Attack',
            },
            auth=self.auth
        ).maybe_follow()

        self.project.reload()
        self.node_settings.reload()

        assert_equal(len(self.project.logs), log_count)
        assert_false(mock_add_hook.called)

    @mock.patch('website.addons.gitlab.api.GitLabClient.repo')
    def test_link_repo_non_existent(self, mock_repo):

        mock_repo.return_value = None

        url = self.project.api_url + 'gitlab/settings/'
        res = self.app.post_json(
            url,
            {
                'gitlab_user': 'queen',
                'gitlab_repo': 'night at the opera',
            },
            auth=self.auth,
            expect_errors=True
        ).maybe_follow()

        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.gitlab.api.GitLabClient.branches')
    def test_link_repo_registration(self, mock_branches):

        mock_branches.return_value = [
            Branch.from_json({
                'name': 'master',
                'commit': {
                    'sha': '6dcb09b5b57875f334f61aebed695e2e4193db5e',
                    'url': 'https://api.gitlab.com/repos/octocat/Hello-World/commits/c5b97d5ae6c19d5c5df71a34c7fbeeda2479ccbc',
                }
            }),
            Branch.from_json({
                'name': 'develop',
                'commit': {
                    'sha': '6dcb09b5b57875asdasedawedawedwedaewdwdass',
                    'url': 'https://api.gitlab.com/repos/octocat/Hello-World/commits/cdcb09b5b57875asdasedawedawedwedaewdwdass',
                }
            })
        ]

        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=self.consolidated_auth,
            data=''
        )

        url = registration.api_url + 'gitlab/settings/'
        res = self.app.post_json(
            url,
            {
                'gitlab_user': 'queen',
                'gitlab_repo': 'night at the opera',
            },
            auth=self.auth,
            expect_errors=True
        ).maybe_follow()

        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.gitlab.model.GitLabNodeSettings.delete_hook')
    def test_deauthorize(self, mock_delete_hook):

        url = self.project.api_url + 'gitlab/user_auth/'

        self.app.delete(url, auth=self.auth).maybe_follow()

        self.project.reload()
        self.node_settings.reload()
        assert_equal(self.node_settings.user, None)
        assert_equal(self.node_settings.repo, None)
        assert_equal(self.node_settings.user_settings, None)

        assert_equal(self.project.logs[-1].action, 'gitlab_node_deauthorized')


if __name__ == '__main__':
    unittest.main()
