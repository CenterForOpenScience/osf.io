#!/usr/bin/env python
# -*- coding: utf-8 -*-
import mock
import unittest
from nose.tools import *  # PEP8 asserts

from tests.base import DbTestCase
from tests.factories import ProjectFactory, AuthUserFactory
from webtest_plus import TestApp

import website.app
from website.addons.github.tests.utils import create_mock_github
from website.addons.github import views
from website.addons.github.model import AddonGitHubNodeSettings
from website.addons.github import api

app = website.app.init_app(routes=True, set_backends=False,
                            settings_module="website.settings")

github_mock = create_mock_github(user='fred', private=False)

class TestGithubViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('github')
        self.project.creator.add_addon('github')

        self.github = github_mock

        self.node_settings = self.project.get_addon('github')
        self.node_settings.user_settings = self.project.creator.get_addon('github')
        # Set the node addon settings to correspond to the values of the mock repo
        self.node_settings.user = self.github.repo.return_value['owner']['login']
        self.node_settings.repo = self.github.repo.return_value['name']
        self.node_settings.save()

    def test_page_content_no_user(self):
        # Addon settings doesn't have a user
        github = AddonGitHubNodeSettings(user=None, repo='foo')
        res = views._page_content(node=self.project, github=github)
        assert_equal(res, {})

    def test_page_content_no_repo(self):
        # Addon settings doesn't have a repo
        github = AddonGitHubNodeSettings(user='fred', repo='bar')
        res = views._page_content(node=self.project, github=github)
        assert_equal(res, {})

    def test_page_content_default_branch(self):
        res = views._page_content(node=self.project, github=self.node_settings,
                                    _connection=self.github)
        self.github.repo.assert_called_with(self.node_settings.user,
                                            self.node_settings.repo)
        assert_equal(res['branch'], self.github.repo.return_value['default_branch'])

    def test_page_content_return_value(self):
        res = views._page_content(node=self.project, github=self.node_settings,
                                _connection=self.github)
        assert_equal(res['gh_user'], 'fred')
        assert_equal(res['repo'], self.github.repo.return_value['name'])
        assert_true(res['is_head'])
        assert_equal(res['branches'], self.github.branches.return_value)
        assert_equal(res['sha'], '')  # No sha provided
        # 'ref' is the default branch since sha nor branch were provided
        assert_equal(res['ref'], self.github.repo.return_value['default_branch'])
        # just check the existence of grid_data
        assert_true(res['grid_data'])
        # same with registration_data
        assert_true(res['registration_data'])

    def test_github_widget(self):
        assert 0, 'finish me'

    def test_github_page(self):
        assert 0, 'finish me'


    @mock.patch('website.addons.github.views.GitHub')
    def test_github_get_repo(self, mock_github):
        assert 0, 'finish me'

    @mock.patch('website.addons.github.views.GitHub', github_mock)
    def test_hgrid_data(self):
        url = '/api/v1/project/{0}/github/hgrid/'.format(self.project._id)
        self.github.tree.return_value = {'tree': [
              {
                "type": "file",
                "size": 625,
                "name": "octokit.rb",
                "path": "lib/octokit.rb",
                "sha": "fff6fe3a23bf1c8ea0692b4a883af99bee26fd3b",
                "url": "https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit.rb",
                "git_url": "https://api.github.com/repos/pengwynn/octokit/git/blobs/fff6fe3a23bf1c8ea0692b4a883af99bee26fd3b",
                "html_url": "https://github.com/pengwynn/octokit/blob/master/lib/octokit.rb",
                "_links": {
                  "self": "https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit.rb",
                  "git": "https://api.github.com/repos/pengwynn/octokit/git/blobs/fff6fe3a23bf1c8ea0692b4a883af99bee26fd3b",
                  "html": "https://github.com/pengwynn/octokit/blob/master/lib/octokit.rb"
                }
              },
              {
                "type": "dir",
                "size": 0,
                "name": "octokit",
                "path": "lib/octokit",
                "sha": "a84d88e7554fc1fa21bcbc4efae3c782a70d2b9d",
                "url": "https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit",
                "git_url": "https://api.github.com/repos/pengwynn/octokit/git/trees/a84d88e7554fc1fa21bcbc4efae3c782a70d2b9d",
                "html_url": "https://github.com/pengwynn/octokit/tree/master/lib/octokit",
                "_links": {
                  "self": "https://api.github.com/repos/pengwynn/octokit/contents/lib/octokit",
                  "git": "https://api.github.com/repos/pengwynn/octokit/git/trees/a84d88e7554fc1fa21bcbc4efae3c782a70d2b9d",
                  "html": "https://github.com/pengwynn/octokit/tree/master/lib/octokit"
                }
              }
            ]
        }
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        gh_tree = self.github.tree(user='octo-cat',
                                    repo='mock-repo', sha='123abc')['tree']
        hgrid_dict = api.tree_to_hgrid(gh_tree, user='octo-cat', repo='mock-repo',
                                        node=self.project)
        assert_equal(res.json, hgrid_dict)


class TestRegistrationsWithGithub(DbTestCase):

    def test_registration_shows_only_commits_on_or_before_registration(self):
        assert 0, 'finish me'

if __name__ == '__main__':
    unittest.main()
