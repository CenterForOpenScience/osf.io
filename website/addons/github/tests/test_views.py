#!/usr/bin/env python
# -*- coding: utf-8 -*-
import httplib as http

import mock
import unittest
import urlparse

from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, UserFactory, AuthUserFactory

import datetime

from github3.git import Commit
from github3.repos.branch import Branch
from github3.repos.contents import Contents

from framework.exceptions import HTTPError
from framework.auth import Auth

from website.util import web_url_for, api_url_for
from website.addons.github.tests.utils import create_mock_github
from website.addons.github import views, api, utils
from website.addons.github.model import GithubGuidFile
from website.addons.github.utils import MESSAGES, check_permissions
from website.addons.github.exceptions import TooBigError

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

    @mock.patch('website.addons.github.views.crud.build_github_urls')
    @mock.patch('website.addons.github.api.GitHub.create_file')
    @mock.patch('website.addons.github.api.GitHub.tree')
    def test_create_file(self, mock_tree, mock_create, mock_urls):
        sha = '12345'
        size = 128
        file_name = 'my_file'
        file_content = 'my_data'
        branch = 'master'
        mock_tree.return_value.tree = []
        mock_create.return_value = {
            'commit': Commit(dict(sha=sha)),
            'content': Contents(dict(size=size, url='http://fake.url/')),
        }
        mock_urls.return_value = {}
        url = self.project.api_url_for('github_upload_file', branch=branch)
        self.app.post(
            url,
            upload_files=[
                ('file', file_name, file_content),
            ],
            auth=self.user.auth,
        )
        mock_create.assert_called_once_with(
            self.node_settings.user,
            self.node_settings.repo,
            file_name,
            MESSAGES['add'],
            file_content,
            branch=branch,
            author={
                'name': self.user.fullname,
                'email': '{0}@osf.io'.format(self.user._id),
            },
        )


    @mock.patch('website.addons.github.api.GitHub.contents')
    @mock.patch('website.addons.github.api.GitHub.from_settings')
    @mock.patch('website.project.views.file.get_cache_content')
    def test_view_file(self, mock_cache, mock_settings, mock_contents):
        github_mock = self.github
        mock_settings.return_value = github_mock
        sha = self.github.tree.return_value.tree[0].sha
        github_mock.history.return_value = [
            {
            'sha': sha,
            'name': 'fred',
            'email': '{0}@osf.io'.format(self.user._id),
            'date': datetime.date(2011, 10, 15).ctime(),
            }
        ]
        mock_cache.return_value = "this is some html"
        guid = GithubGuidFile()
        path = github_mock.tree.return_value.tree[0].path
        guid.path = path
        guid.node = self.project
        guid.save()
        mock_contents.return_value.sha = sha
        github_mock.contents.return_value = mock_contents
        github_mock.file.return_value = (' ', ' ', 255)
        url = self.project.web_url_for(
            'github_view_file',
            sha = sha,
            path = path
        )
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert_equal(res.status_code, 302)
        res2 = res.follow(auth=self.user.auth)
        assert_equal(res2.request.path, '/{0}/'.format(guid._id))
        assert_equal(res2.status_code, 200)


    @mock.patch('website.addons.github.api.GitHub.from_settings')
    @mock.patch('website.addons.github.views.crud.build_github_urls')
    def test_update_file(self, mock_urls, mock_settings):
        github_mock = self.github
        sha = github_mock.tree.return_value.tree[0].sha
        size = github_mock.tree.return_value.tree[0].size
        file_name = github_mock.tree.return_value.tree[0].path
        file_content = 'my_data'
        branch = 'master'
        mock_settings.return_value = github_mock
        github_mock.update_file.return_value = {
            'commit': Commit(dict(sha=sha)),
            'content': Contents(dict(size=size, url='http://fake.url/')),
        }
        mock_urls.return_value = {}
        url = self.project.api_url_for('github_upload_file', branch=branch, sha=sha)
        self.app.post(
            url,
            upload_files=[
                ('file', file_name, file_content),
            ],
            auth=self.user.auth,
        )
        github_mock.update_file.assert_called_once_with(
            self.node_settings.user,
            self.node_settings.repo,
            file_name,
            MESSAGES['update'],
            file_content,
            sha=sha,
            branch=branch,
            author={
                'name': self.user.fullname,
                'email': '{0}@osf.io'.format(self.user._id),
            },
        )


    @mock.patch('website.addons.github.api.GitHub.file')
    def test_download_file(self, mock_file):
        file_name = 'my_file'
        file_content = 'my_content'
        file_size = 1024
        mock_file.return_value = (file_name, file_content, file_size)
        url = self.project.web_url_for(
            'github_download_file',
            path='my_file',
            branch='master',
        )
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert_equal(res.body, file_content)


    @mock.patch('website.addons.github.api.GitHub.file')
    def test_download_file_too_big(self, mock_file):
        mock_file.side_effect = TooBigError
        url = self.project.web_url_for(
            'github_download_file',
            path='my_file',
            branch='master',
        )
        res = self.app.get(
            url,
            auth=self.user.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)


    @mock.patch('website.addons.github.api.GitHub.from_settings')
    @mock.patch('website.addons.github.api.GitHub.delete_file')
    @mock.patch('website.addons.github.api.GitHub.file')
    def test_delete_file(self, mock_file, mock_delete, mock_settings):
        github_mock = self.github
        sha = github_mock.tree.return_value.tree[0].sha
        size = github_mock.tree.return_value.tree[0].size
        file_name = github_mock.tree.return_value.tree[0].path
        branch = 'master'
        mock_settings.return_value = github_mock
        github_mock.delete_file.return_value = {
            'commit': Commit(dict(sha=sha)),
        }
        url = self.project.api_url_for('github_delete_file', sha=sha, path=file_name, branch=branch)
        self.app.delete(
            url,
            auth=self.user.auth,
        )
        github_mock.delete_file.assert_called_once_with(
            self.node_settings.user,
            self.node_settings.repo,
            file_name,
            MESSAGES['delete'],
            sha=sha,
            branch=branch,
            author={
                'name': self.user.fullname,
                'email': '{0}@osf.io'.format(self.user._id),
            },
        )

class TestHGridViews(OsfTestCase):

    def setUp(self):
        super(TestHGridViews, self).setUp()
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

    def test_to_hgrid(self):
        github_mock = self.github
        contents = github_mock.contents(user='octocat', repo='hello', ref='12345abc')
        res = views.hgrid.to_hgrid(
            contents,
            node_url=self.project.url, node_api_url=self.project.api_url,
            max_size=10
        )

        assert_equal(len(res), 2)
        assert_equal(res[0]['addon'], 'github')
        assert_true(res[0]['permissions']['view'])  # can always view
        expected_kind = 'item' if contents['octokit'].type == 'file' else 'folder'
        assert_equal(res[0]['kind'], expected_kind)
        assert_equal(res[0]['accept']['maxSize'], 10)
        assert_equal(res[0]['accept']['acceptedFiles'], None)
        assert_equal(res[0]['urls'], api.build_github_urls(contents['octokit'],
            self.project.url, self.project.api_url, branch=None, sha=None))
        # Files should not have lazy-load or upload URLs
        assert_not_in('lazyLoad', res[0])
        assert_not_in('uploadUrl', res[0])

    # TODO: Test to_hgrid with branch and sha arguments


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
        self.project.save()
        self.project.add_addon('github', auth=self.consolidated_auth)
        self.project.creator.add_addon('github')

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

    @mock.patch('website.addons.github.model.AddonGitHubUserSettings.has_auth')
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
    @mock.patch('website.addons.github.model.AddonGitHubUserSettings.has_auth')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_permissions_no_access(self, mock_repo, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        branch = 'master'
        mock_repository = mock.NonCallableMock()
        mock_repository.user = 'fred'
        mock_repository.repo = 'mock-repo'
        mock_repository.to_json.return_value = {'user': 'fred',
                                                'repo': 'mock-repo',
                                                'permissions': {
                                                    'push': False, # this is key
                                                    },
                                               }
        mock_repo.return_value = mock_repository
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, branch, repo=mock_repository))


    # make a branch with a different commit than the commit being passed into check_permissions
    @mock.patch('website.addons.github.model.AddonGitHubUserSettings.has_auth')
    def test_permissions_not_head(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        mock_branch = mock.NonCallableMock()
        mock_branch.commit.sha = '67890'
        sha = '12345'
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, mock_branch, sha=sha))


    # make sure permissions are not granted for editing a registration
    @mock.patch('website.addons.github.model.AddonGitHubUserSettings.has_auth')
    def test_permissions(self, mock_has_auth):
        github_mock = self.github
        mock_has_auth.return_value = True
        connection = github_mock
        self.node_settings.owner.is_registration = True
        assert_false(check_permissions(self.node_settings, self.consolidated_auth, connection, 'master'))


    # TODO: Write me
    def test_dummy_folder(self):
        pass

    def test_dummy_folder_parent(self):
        pass

    def test_dummy_folder_refs(self):
        pass

    # TODO: Write me
    def test_github_contents(self):
        pass

    def check_hook_urls(self, urls, node, path, sha):
        assert_equal(
            urls['view'],
            node.web_url_for(
                'github_view_file',
                path=path,
                sha=sha,
            ),
        )
        assert_equal(
            urls['download'],
            node.web_url_for(
                'github_download_file',
                path=path,
                sha=sha,
            ),
        )

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

    @mock.patch('website.addons.github.api.GitHub.history')
    @mock.patch('website.addons.github.api.GitHub.contents')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_view_not_found_does_not_create_guid(self, mock_repo, mock_contents, mock_history):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value
        mock_contents.return_value = github_mock.contents.return_value['octokit']
        mock_history.return_value = []

        guid_count = GithubGuidFile.find().count()

        # View file for the first time
        # Because we've overridden mock_history above, it doesn't matter if the
        #   file exists.
        url = self.project.web_url_for('github_view_file', path='test.py')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)

        assert_equal(
            404,
            res.status_code,
        )

        guids = GithubGuidFile.find()

        # GUID count has not changed
        assert_equal(
            guids.count(),
            guid_count,
        )

    @mock.patch('website.addons.github.api.GitHub.history')
    @mock.patch('website.addons.github.api.GitHub.contents')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_view_creates_guid(self, mock_repo, mock_contents, mock_history):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value
        mock_contents.return_value = github_mock.contents.return_value['octokit']
        mock_history.return_value = github_mock.commits.return_value

        guid_count = GithubGuidFile.find().count()

        # View file for the first time
        # Because we've overridden mock_history above, it doesn't matter if the
        #   file exists.
        url = self.project.web_url_for('github_view_file', path='test.py')
        res = self.app.get(url, auth=self.user.auth)

        guids = GithubGuidFile.find()

        # GUID count has been incremented by one
        assert_equal(
            guids.count(),
            guid_count + 1
        )

        file_guid = guids[guids.count() - 1]._id
        file_url = web_url_for('resolve_guid', guid=file_guid)

        # Client has been redirected to GUID
        assert_equal(
            302,
            res.status_code
        )
        assert_equal(
            file_url,
            urlparse.urlparse(res.location).path
        )

        # View the file
        res = self.app.get(file_url, auth=self.user.auth)

        assert_equal(
            200,
            res.status_code
        )

        # View file for the second time
        self.app.get(file_url, auth=self.user.auth)

        # GUID count has not been incremented
        assert_equal(
            GithubGuidFile.find().count(),
            guid_count + 1
        )

    ######################
    # This test currently won't work with webtest; self.app.get() fails
    # on a url containing Unicode.
    #
    # In addition, this test currently is incorrect: it really just ensures
    # a guid is created for the file
    #
    # @mambocab
    #
    # @mock.patch('website.addons.github.api.GitHub.history')
    # @mock.patch('website.addons.github.api.GitHub.contents')
    # @mock.patch('website.addons.github.api.GitHub.repo')
    # def test_file_view(self, mock_repo, mock_contents, mock_history):
    #
    #     mock_repo.return_value = github_mock.repo.return_value
    #     mock_contents.return_value = github_mock.contents.return_value['octokit.rb']
    #     mock_history.return_value = github_mock.commits.return_value
    #
    #     # View file for the first time
    #     url = self.project.url + 'github/file/' + mock_contents.return_value.name
    #     res = self.app.get(url, auth=self.user.auth).maybe_follow(auth=self.user.auth)
    #
    #     guids = GithubGuidFile.find()
    #
    #     # Client has been redirected to GUID
    #     assert_in(
    #         guids[guids.count() - 1]._id,
    #         res.request.path
    #     )


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

    @mock.patch('website.addons.github.api.GitHub.branches')
    def test_registration_shows_only_commits_on_or_before_registration(self, mock_branches):

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
        registration = ProjectFactory()
        clone, message = self.node_settings.after_register(
            self.project, registration, self.project.creator,
        )
        mock_branches.assert_called_with(
            self.node_settings.user,
            self.node_settings.repo,
        )
        rv = [
            Branch.from_json({
                'name': 'master',
                'commit': {
                    'sha': 'danwelndwakjefnawjkefwe2e4193db5essssssss',
                    'url': 'https://api.github.com/repos/octocat/Hello-World/commits/dasdsdasdsdaasdsadsdasdsdac7fbeeda2479ccbc',
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
        assert_equal(
            self.node_settings.user,
            clone.user,
        )
        assert_equal(
            self.node_settings.repo,
            clone.repo,
        )
        assert_in(
            rv[1].to_json(),
            clone.registration_data['branches']
        )
        assert_not_in(
            rv[0].to_json(),
            clone.registration_data['branches']
        )
        assert_equal(
            clone.user_settings,
            self.node_settings.user_settings
        )


class TestGithubSettings(OsfTestCase):

    def setUp(self):

        super(TestGithubSettings, self).setUp()
        self.github = create_mock_github(user='fred', private=False)
        self.project = ProjectFactory.build()
        self.project.save()
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

    @mock.patch('website.addons.github.model.AddonGitHubNodeSettings.add_hook')
    @mock.patch('website.addons.github.api.GitHub.repo')
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
        assert_equal(self.project.logs[-1].action, 'github_repo_linked')
        mock_add_hook.assert_called_once()

    @mock.patch('website.addons.github.model.AddonGitHubNodeSettings.add_hook')
    @mock.patch('website.addons.github.api.GitHub.repo')
    def test_link_repo_no_change(self, mock_repo, mock_add_hook):
        github_mock = self.github
        mock_repo.return_value = github_mock.repo.return_value

        log_count = len(self.project.logs)

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

        assert_equal(len(self.project.logs), log_count)
        assert_false(mock_add_hook.called)

    @mock.patch('website.addons.github.api.GitHub.repo')
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
            None, self.consolidated_auth, '', ''
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

    @mock.patch('website.addons.github.model.AddonGitHubNodeSettings.delete_hook')
    def test_deauthorize(self, mock_delete_hook):

        url = self.project.api_url + 'github/oauth/'

        self.app.delete(url, auth=self.auth).maybe_follow()

        self.project.reload()
        self.node_settings.reload()
        assert_equal(self.node_settings.user, None)
        assert_equal(self.node_settings.repo, None)
        assert_equal(self.node_settings.user_settings, None)

        assert_equal(self.project.logs[-1].action, 'github_node_deauthorized')


class TestAuthViews(OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.user = AuthUserFactory()
        self.user.add_addon('github')
        self.user.save()
        self.user_settings = self.user.get_addon('github')

    def test_oauth_callback_with_invalid_user(self):
        url = api_url_for('github_oauth_callback', uid="")
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_oauth_callback_with_invalid_node(self):
        url = api_url_for('github_oauth_callback', uid=self.user._id, nid="")
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_oauth_callback_without_github_enabled(self):
        user2 = AuthUserFactory()
        url = api_url_for('github_oauth_callback', uid=user2._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_oauth_callback_with_no_code(self):
        url = api_url_for('github_oauth_callback', uid=self.user._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 400)


    @mock.patch('website.addons.github.api.GitHub.user')
    @mock.patch('website.addons.github.views.auth.oauth_get_token')
    def test_oauth_callback_without_node(self, mock_get_token, mock_github_user):
        mock_get_token.return_value = {
            "access_token": "testing access token",
            "token_type": "testing token type",
            "scope": ["repo"]
        }
        user = mock.Mock()
        user.id = "testing user id"
        user.login = "testing user"
        mock_github_user.return_value = user

        url = api_url_for('github_oauth_callback', uid=self.user._id)
        res = self.app.get(url, {"code": "12345"}, auth=self.user.auth)
        self.user_settings.reload()
        assert_true(res.status_code, 302)
        assert_in("/settings/addons/", res.location)
        assert_true(self.user_settings.oauth_settings)
        assert_equal(self.user_settings.oauth_access_token, "testing access token")
        assert_equal(self.user_settings.oauth_token_type, "testing token type")
        assert_equal(self.user_settings.github_user_name, "testing user")
        assert_equal(self.user_settings.oauth_settings.github_user_id, "testing user id")


    @mock.patch('website.addons.github.api.GitHub.user')
    @mock.patch('website.addons.github.views.auth.oauth_get_token')
    def test_oauth_callback_with_node(self, mock_get_token, mock_github_user):
        mock_get_token.return_value = {
            "access_token": "testing access token",
            "token_type": "testing token type",
            "scope": ["repo"]
        }
        user = mock.Mock()
        user.id = "testing user id"
        user.login = "testing user"
        mock_github_user.return_value = user

        project = ProjectFactory(creator=self.user)
        project.add_addon('github', auth=Auth(user=self.user))
        project.save()

        url = api_url_for('github_oauth_callback', uid=self.user._id, nid=project._id)
        res = self.app.get(url, {"code": "12345"}, auth=self.user.auth)
        self.user_settings.reload()

        node_settings = project.get_addon('github')
        node_settings.reload()

        assert_true(res.status_code, 302)
        assert_not_in("/settings/addons/", res.location)
        assert_in("/settings", res.location)
        assert_true(self.user_settings.oauth_settings)
        assert_equal(self.user_settings.oauth_access_token, "testing access token")
        assert_equal(self.user_settings.oauth_token_type, "testing token type")
        assert_equal(self.user_settings.github_user_name, "testing user")
        assert_equal(self.user_settings.oauth_settings.github_user_id, "testing user id")
        assert_equal(node_settings.user_settings, self.user_settings)



    @mock.patch('website.addons.github.api.GitHub.user')
    def test_create_and_attach_oauth(self, mock_github_user):
        user = mock.Mock()
        user.id = "testing user id"
        user.login = "testing user"
        mock_github_user.return_value = user
        views.auth.create_and_attach_oauth(self.user_settings, "testing access token", "testing token type")
        assert_true(self.user_settings.oauth_settings)
        assert_false(self.user_settings.oauth_state)
        assert_equal(
            self.user_settings.github_user_name,
            "testing user"
        )
        assert_equal(
            self.user_settings.oauth_access_token,
            "testing access token"
        )
        assert_equal(
            self.user_settings.oauth_token_type,
            "testing token type"
        )
        assert_equal(
            self.user_settings.oauth_settings.github_user_id,
            "testing user id"
        )

    @mock.patch('website.addons.github.api.GitHub.user')
    @mock.patch('website.addons.github.api.GitHub.revoke_token')
    def test_oauth_delete_user_one_osf_user(self, mock_revoke_token, mock_github_user):
        mock_revoke_token.return_value = True
        user = mock.Mock()
        user.id = "testing user id"
        user.login = "testing user"
        mock_github_user.return_value = user
        views.auth.create_and_attach_oauth(self.user_settings, "testing access token", "testing token type")
        url = api_url_for("github_oauth_delete_user")
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_false(self.user_settings.oauth_token_type)
        assert_false(self.user_settings.oauth_access_token)
        assert_false(self.user_settings.github_user_name)
        assert_false(self.user_settings.oauth_settings)

    @mock.patch('website.addons.github.api.GitHub.user')
    @mock.patch('website.addons.github.api.GitHub.revoke_token')
    def test_oauth_delete_user_two_osf_user(self, mock_revoke_token, mock_github_user):
        mock_revoke_token.return_value = True
        user = mock.Mock()
        user.id = "testing user id"
        user.login = "testing user"
        mock_github_user.return_value = user
        views.auth.create_and_attach_oauth(self.user_settings, "testing acess token", "testing token type")

        user2 = AuthUserFactory()
        user2.add_addon('github')
        user2.save()
        user_settings2 = user2.get_addon('github')
        views.auth.create_and_attach_oauth(user_settings2, "testing access token", "testing token type")

        url = api_url_for("github_oauth_delete_user")
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        user_settings2.reload()
        assert_false(self.user_settings.oauth_token_type)
        assert_false(self.user_settings.oauth_access_token)
        assert_false(self.user_settings.github_user_name)
        assert_false(self.user_settings.oauth_settings)
        assert_true(user_settings2.oauth_settings)
        assert_equal(user_settings2.oauth_token_type, "testing token type")
        assert_equal(user_settings2.oauth_access_token, "testing access token")
        assert_equal(user_settings2.github_user_name, "testing user")

if __name__ == '__main__':
    unittest.main()
