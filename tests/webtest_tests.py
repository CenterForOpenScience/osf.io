#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Functional tests using WebTest.'''
import unittest
import datetime as dt
from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp

from tests.base import DbTestCase
from tests.factories import (UserFactory, ProjectFactory, WatchConfigFactory,
                            NodeLogFactory, ApiKeyFactory)

from framework import app
from website import settings

# Only uncomment if running these tests in isolation
# from website.app import init_app
# app = init_app(set_backends=False, routes=True)

class TestAnUnregisteredUser(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)

    def test_can_register(self):
        # Goes to home page
        res = self.app.get("/").maybe_follow()
        # Clicks sign in button
        res = res.click("Create an Account or Sign-In").maybe_follow()
        # Fills out registration form
        form = res.forms['registerForm']
        form['register-fullname'] = "Nicholas Cage"
        form['register-username'] = "nickcage@example.com"
        form['register-username2'] = "nickcage@example.com"
        form['register-password'] = "example"
        form['register-password2'] = "example"
        # Submits
        res = form.submit().follow()
        # There's a flash message
        assert_in("You may now log in", res)
        # User logs in
        form = res.forms['signinForm']
        form['username'] = "nickcage@example.com"
        form['password'] = "example"
        # Submits
        res = form.submit().maybe_follow()

    def test_sees_error_if_email_is_already_registered(self):
        # A user is already registered
        user = UserFactory(username="foo@bar.com")
        # Goes to home page
        res = self.app.get("/").maybe_follow()
        # Clicks sign in button
        res = res.click("Create an Account or Sign-In").maybe_follow()
        # Fills out registration form
        form = res.forms['registerForm']
        form['register-fullname'] = "Foo Bar"
        form['register-username'] = "foo@bar.com"
        form['register-username2'] = "foo@bar.com"
        form['register-password'] = "example"
        form['register-password2'] = "example"
        # submits
        res = form.submit().maybe_follow()
        # sees error message because email is already registered
        assert_in("has already been registered.", res)


class TestAUser(DbTestCase):

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
        res = form.submit().maybe_follow()
        return res

    def test_can_see_homepage(self):
        # Goes to homepage
        res = self.app.get("/").follow()  # Redirects
        assert_equal(res.status_code, 200)

    def test_can_log_in(self):
        # Goes to home page
        res = self.app.get("/").follow()
        # Clicks sign in button
        res = res.click("Create an Account or Sign-In").maybe_follow()
        # Fills out login info
        form = res.forms['signinForm']  # Get the form from its ID
        form['username'] = self.user.username
        form['password'] = 'science'
        # submits
        res = form.submit().maybe_follow()
        # Sees dashboard with projects and watched projects
        assert_in("Projects", res)
        assert_in("Watched Projects", res)

    def test_sees_flash_message_on_bad_login(self):
        # Goes to log in page
        res = self.app.get("/account/").maybe_follow()
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
        res = self.app.get("/").maybe_follow()
        # Clicks Dashboard link in navbar
        res = res.click("Dashboard", index=0)
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

    def test_can_create_a_project(self):
        res = self._login(self.user.username, 'science')
        # Goes to dashboard (already logged in)
        res = res.click("My Dashboard", index=0)
        # Clicks New Project
        res = res.click("New Project").maybe_follow()
        # Fills out the form
        form = res.forms['projectForm']
        form['title'] = "My new project"
        form['description'] = "Just testing"
        # Submits
        res = form.submit().maybe_follow()
        # Taken to the project's page
        assert_in("My new project", res)

    def test_sees_correct_title_home_page(self):
        # User goes to homepage
        res = self.app.get("/", auto_follow=True)
        title = res.html.title.string
        # page title is correct
        assert_equal("Open Science Framework | Home", title)

    def test_sees_correct_title_on_dashboard(self):
        # User goes to dashboard
        res = self.app.get("/dashboard/", auth=self.auth, auto_follow=True)
        title = res.html.title.string
        assert_equal("Open Science Framework | Dashboard", title)

    def test_can_see_make_public_button_if_contributor(self):
        # User is a contributor on a project
        project = ProjectFactory()
        project.add_contributor(self.user)
        project.save()
        # User goes to the project page
        res = self.app.get("/project/{0}/".format(project._primary_key), auth=self.auth).maybe_follow()
        assert_in("Make public", res)

    def test_sees_logs_on_a_project(self):
        project = ProjectFactory(is_public=True)
        # User goes to the project's page
        res = self.app.get("/project/{0}/".format(project._primary_key), auth=self.auth).maybe_follow()
        # Can see log event
        # res.showbrowser()
        assert_in("created", res)

    def test_no_wiki_content_message(self):
        project = ProjectFactory(creator=self.user)
        # Goes to project's wiki, where there is no content
        res = self.app.get("/project/{0}/wiki/home/".format(project._primary_key), auth=self.auth)
        # Sees a message indicating no content
        assert_in("No wiki content", res)

    def test_cant_delete_registration(self):
        original = ProjectFactory(creator=self.user, is_public=True)
        # A registration
        project = ProjectFactory(is_registration=True,
                                registered_from=original,
                                registered_date=dt.datetime.now(),
                                creator=self.user)
        # Goes to project's page
        res = self.app.get("/project/{0}/".format(project._primary_key), auth=self.auth).maybe_follow()
        # Can't get to settings
        assert_not_in("Settings", res)


# TODO: These affect search in development environment. So need to migrate solr after running.
# # Remove this side effect.
@unittest.skipIf(not settings.USE_SOLR, "Skipping because USE_SOLR is False")
class TestSearching(DbTestCase):

    '''Test searching using the search bar. NOTE: These may affect the
    Solr database. May need to migrate after running these.
    '''

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory()
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)

    def test_a_user_from_home_page(self):
        user = UserFactory()
        # Goes to home page
        res = self.app.get("/").maybe_follow()
        # Fills search form
        form = res.forms['searchBar']
        form['q'] = user.fullname
        res = form.submit().maybe_follow()
        # No results, so clicks Search Users
        res = res.click("Search users")
        # The username shows as a search result
        assert_in(user.fullname, res)

    def test_a_public_project_from_home_page(self):
        project = ProjectFactory(title="Foobar Project", is_public=True)
        # Searches a part of the name
        res = self.app.get('/').maybe_follow()
        project.reload()
        form = res.forms['searchBar']
        form['q'] = "Foobar"
        res = form.submit().maybe_follow()
        # A link to the project is shown as a result
        assert_in("Foobar Project", res)


if __name__ == '__main__':
    unittest.main()
