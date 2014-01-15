import unittest
import mock
from nose.tools import *  # PEP8 asserts
import json
from tests.base import DbTestCase
from tests.factories import ProjectFactory, UserFactory, AuthUserFactory
from website.addons.github.tests.utils import create_mock_github
from website.addons.github import views
from website.addons.github.model import AddonGitHubNodeSettings


from webtest_plus import TestApp
import website.app
app = website.app.init_app(routes=True, set_backends=False,
                            settings_module="website.settings")


class TestGitHubPage(DbTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
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

    def test_can_see_github_tab(self):
        url = "/project/{0}/".format(self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_in('a href="/{0}/github"'.format(self.project._id), res)

    def test_github_page_with_auth(self):
        url = "/project/{0}/github/".format(self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_in("/addons/static/github/hgrid-github.js", res)
        assert_in("/addons/static/github/comicon.png", res)
        assert_in("/{0}/github".format(self.project._id), res)

    def test_github_page_without_auth(self):
        self.node_settings.user = "nosense"
        self.node_settings.save()
        url = "/project/{0}/github/".format(self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_in(" GitHub add-on is not configured properly. Configure this add-on", res)

    def test_github_widget_present(self):
        url = "/project/{0}/".format(self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_in('a href="/{0}/github"'.format(self.project._id), res)
        assert_in('<span>GitHub</span>', res)
        
    def test_github_widget_without_auth(self):
        self.node_settings.user = "nosense"
        self.node_settings.save()
        url = "/project/{0}/".format(self.project._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_in(" GitHub add-on is not configured properly. Configure this add-on", res)