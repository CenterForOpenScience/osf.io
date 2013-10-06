#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Functional tests using WebTest.'''
import unittest
from nose.tools import *  # PEP8 asserts

from tests.base import OsfTestCase, TestApp
from tests.factories import (UserFactory, ProjectFactory, WatchConfigFactory,
                            NodeLogFactory, ApiKeyFactory)

from framework import app

import new_style  # This import sets up the routes


class TestAUser(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory(password='science')
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)

    def _login(self, username, password):
        '''Log in a user via at the login page.'''
        res = self.app.get("/account/").maybe_follow()
        # Fills out login info
        form = res.forms['signinForm']  # Get the form from its ID
        form['username'] = self.user.username
        form['password'] = 'science'
        # submits
        res = form.submit().follow()
        return res

    def test_can_see_homepage(self):
        # Goes to homepage
        res = self.app.get("/").follow()  # Redirects
        assert_equal(res.status_code, 200)

    def test_can_log_in(self):
        # Goes to home page
        res = self.app.get("/").follow()
        # Clicks sign in button
        res = res.click("Create an Account or Sign-In").follow()
        # Fills out login info
        form = res.forms['signinForm']  # Get the form from its ID
        form['username'] = self.user.username
        form['password'] = 'science'
        # submits
        # res.showbrowser()
        res = form.submit().follow()
        # Sees dashboard with projects and watched projects
        assert_in("Projects", res)
        assert_in("Watched Projects", res)

    def test_sees_flash_message_on_bad_login(self):
        # Goes to log in page
        res = self.app.get("/account/").follow()
        # Fills the form with incorrect password
        form  = res.forms['signinForm']
        form['username'] = self.user.username
        form['password'] = 'thisiswrong'
        # Submits
        res = form.submit()
        # Sees a flash message
        assert_in("Log-in failed", res)

    def test_sees_projects_in_her_dashboard(self):
        # the user already has a project
        project = ProjectFactory(creator=self.user)
        project.add_contributor(self.user)
        project.save()
        # Goes to homepage, already logged in
        res = self._login(self.user.username, 'science')
        res = self.app.get("/", auto_follow=True)
        # Clicks Dashboard link in navbar
        res = res.click("Dashboard")
        assert_in("Projects", res)  # Projects heading
        # The project title is listed
        assert_in(project.title, res)


    def test_sees_log_events_on_watched_projects(self):
        # Another user has a public project
        u2 = UserFactory(username="bono@u2.com", fullname="Bono")
        key = ApiKeyFactory()
        u2.api_keys.append(key)
        u2.save()
        project = ProjectFactory(creator=u2, is_public=True)
        project.add_contributor(u2)
        # A file was added to the project
        project.add_file(user=u2, api_key=key, file_name="test.html",
                        content="123", size=2, content_type="text/html")
        project.save()
        # User watches the project
        watch_config = WatchConfigFactory(node=project)
        self.user.watch(watch_config)
        self.user.save()
        # Goes to her dashboard, already logged in
        res = self.app.get("/dashboard/", auth=self.auth, auto_follow=True)
        # Sees logs for the watched project
        assert_in("Watched Projects", res)  # Watched Projects header
        # res.showbrowser()
        # The log action is in the feed
        assert_in("added file test.html", res)
        assert_in(project.title, res)


if __name__ == '__main__':
    unittest.main()
