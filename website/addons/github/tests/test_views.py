#!/usr/bin/env python
# -*- coding: utf-8 -*-
import unittest
from nose.tools import *  # PEP8 asserts
import json
from tests.base import DbTestCase
from tests.factories import ProjectFactory, UserFactory
from website.addons.github.tests.utils import create_mock_github
from website.addons.github import views
from website.addons.github.model import AddonGitHubNodeSettings


from webtest_plus import TestApp
import website.app
app = website.app.init_app(routes=True, set_backends=False,
                            settings_module="website.settings")


class TestGithubViews(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.app = TestApp(app)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('github')
        self.project.creator.add_addon('github')

        self.github = create_mock_github(user='fred', private=False)

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
        assert_true(res['has_auth'], self.github.repo.return_value['permissions']['push'])
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

    def test_github_get_repo(self):
        assert 0, 'finish me'

    def test_hook_callback_add_file_not_thro_osf(self):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        res = self.app.post(
            url,
            json.dumps(
                {"test": True,
                 "commits": [{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct":True,
                              "message":"foo",
                              "timestamp":"2014-01-08T14:15:51-08:00",
                              "url":"https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author":{"name":"Illidan","email":"njqpw@osf.io"},
                              "committer":{"name":"Testor","email":"test@osf.io","username":"tester"},
                              "added":["PRJWN3TV"],"removed":[],"modified":[]}]}
            ),
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "github_file_added")

    def test_hook_callback_modify_file_not_thro_osf(self):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        res = self.app.post(
            url,
            json.dumps(
                {"test": True,
                 "commits": [{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct":True,
                              "message":"foo",
                              "timestamp":"2014-01-08T14:15:51-08:00",
                              "url":"https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author":{"name":"Illidan","email":"njqpw@osf.io"},
                              "committer":{"name":"Testor","email":"test@osf.io","username":"tester"},
                              "added":[],"removed":[],"modified":["PRJWN3TV"]}]}

            ),
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "github_file_updated")

    def test_hook_callback_remove_file_not_thro_osf(self):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        res = self.app.post(
            url,
            json.dumps(
                {"test": True,
                 "commits": [{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct":True,
                              "message":"foo",
                              "timestamp":"2014-01-08T14:15:51-08:00",
                              "url":"https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author":{"name":"Illidan","email":"njqpw@osf.io"},
                              "committer":{"name":"Testor","email":"test@osf.io","username":"tester"},
                              "added":[],"removed":["PRJWN3TV"],"modified":[]}]}
            ),
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs[-1].action, "github_file_removed")

    def test_hook_callback_add_file_thro_osf(self):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        res = self.app.post(
            url,
            json.dumps(
                {"test": True,
                 "commits": [{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct":True,
                              "message":"Added via the Open Science Framework",
                              "timestamp":"2014-01-08T14:15:51-08:00",
                              "url":"https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author":{"name":"Illidan","email":"njqpw@osf.io"},
                              "committer":{"name":"Testor","email":"test@osf.io","username":"tester"},
                              "added":["PRJWN3TV"],"removed":[],"modified":[]}]}
            ),
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "github_file_added")

    def test_hook_callback_modify_file_thro_osf(self):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        res = self.app.post(
            url,
            json.dumps(
                {"test": True,
                 "commits": [{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct":True,
                              "message":"Updated via the Open Science Framework",
                              "timestamp":"2014-01-08T14:15:51-08:00",
                              "url":"https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author":{"name":"Illidan","email":"njqpw@osf.io"},
                              "committer":{"name":"Testor","email":"test@osf.io","username":"tester"},
                              "added":[],"removed":[],"modified":["PRJWN3TV"]}]}

            ),
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "github_file_updated")

    def test_hook_callback_remove_file_thro_osf(self):
        url = "/api/v1/project/{0}/github/hook/".format(self.project._id)
        res = self.app.post(
            url,
            json.dumps(
                {"test": True,
                 "commits": [{"id":"b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "distinct":True,
                              "message":"Deleted via the Open Science Framework",
                              "timestamp":"2014-01-08T14:15:51-08:00",
                              "url":"https://github.com/tester/addontesting/commit/b08dbb5b6fcd74a592e5281c9d28e2020a1db4ce",
                              "author":{"name":"Illidan","email":"njqpw@osf.io"},
                              "committer":{"name":"Testor","email":"test@osf.io","username":"tester"},
                              "added":[],"removed":["PRJWN3TV"],"modified":[]}]}
            ),
            content_type="application/json").maybe_follow()
        self.project.reload()
        assert_not_equal(self.project.logs[-1].action, "github_file_removed")


class TestRegistrationsWithGithub(DbTestCase):

    def test_registration_shows_only_commits_on_or_before_registration(self):
        assert 0, 'finish me'

if __name__ == '__main__':
    unittest.main()
