#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Functional tests using WebTest.'''
import unittest
import re
import datetime as dt
from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp
from webtest import AppError

from tests.base import DbTestCase
from tests.factories import (UserFactory, ProjectFactory, WatchConfigFactory,
                            NodeLogFactory, ApiKeyFactory, NodeFactory,
                            NodeWikiFactory, RegistrationFactory)

from website import settings
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.project.model import ensure_schemas
from framework import app


# Only uncomment if running these tests in isolation
#from website.app import init_app
#app = init_app(set_backends=False, routes=True)


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

    def test_cant_see_new_project_form(self):
        """ Can't see new project form if not logged in. """
        assert_in(
            'You must log in to access this resource',
            self.app.get('/project/new/').maybe_follow()
        )

    def test_cant_see_profile(self):
        """ Can't see profile if not logged in. """
        assert_in(
            'You must log in to access this resource',
            self.app.get('/profile/').maybe_follow()
        )


class TestAUser(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory()
        self.user.set_password('science')
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

    def test_can_see_profile_url(self):
        res = self.app.get(self.user.url).maybe_follow()
        assert_in(self.user.url, res)

    def test_can_see_homepage(self):
        # Goes to homepage
        res = self.app.get('/').maybe_follow()  # Redirects
        assert_equal(res.status_code, 200)

    def test_can_log_in_first_time(self):
        # Goes to home page
        res = self.app.get('/').maybe_follow()
        # Clicks sign in button
        res = res.click('Create an Account or Sign-In').maybe_follow()
        # Fills out login info
        form = res.forms['signinForm']  # Get the form from its ID
        form['username'] = self.user.username
        form['password'] = 'science'
        # submits
        res = form.submit().maybe_follow()
        # Sees dashboard with projects and watched projects
        assert_in('Account Settings', res)

    def test_can_log_in(self):
        # Log in and out
        self._login(self.user.username, 'science')
        self.app.get('/logout/')
        # Goes to home page
        res = self.app.get('/').maybe_follow()
        # Clicks sign in button
        res = res.click('Create an Account or Sign-In').maybe_follow()
        # Fills out login info
        form = res.forms['signinForm']  # Get the form from its ID
        form['username'] = self.user.username
        form['password'] = 'science'
        # submits
        res = form.submit().maybe_follow()
        # Sees dashboard with projects and watched projects
        assert_in('Projects', res)
        assert_in('Watched Projects', res)

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

    @unittest.skip("Can't test this, since logs are dynamically loaded")
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
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_in("Make public", res)

    def test_sees_logs_on_a_project(self):
        project = ProjectFactory(is_public=True)
        # User goes to the project's page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        # Can see log event
        # res.showbrowser()
        assert_in("created", res)

    def test_no_wiki_content_message(self):
        project = ProjectFactory(creator=self.user)
        # Goes to project's wiki, where there is no content
        res = self.app.get("/{0}/wiki/home/".format(project._primary_key), auth=self.auth)
        # Sees a message indicating no content
        assert_in("No wiki content", res)

    def test_sees_own_profile(self):
        res = self.app.get('/profile/', auth=self.auth)
        td1 = res.html.find('td', text=re.compile(r'Public Profile'))
        td2 = td1.find_next_sibling('td')
        assert_equal(td2.text, self.user.display_absolute_url)

    def test_sees_another_profile(self):
        user2 = UserFactory()
        res = self.app.get(user2.url, auth=self.auth)
        td1 = res.html.find('td', text=re.compile(r'Public Profile'))
        td2 = td1.find_next_sibling('td')
        assert_equal(td2.text, user2.display_absolute_url)


class TestRegistrations(DbTestCase):

    def setUp(self):
        ensure_schemas()
        self.app = TestApp(app)
        self.user = UserFactory()
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)
        self.original = ProjectFactory(creator=self.user, is_public=True)
        # A registration
        self.project = RegistrationFactory(
            project=self.original,
            user=self.user,
        )

    def test_cant_be_deleted(self):
        # Goes to project's page
        res = self.app.get(self.project.url, auth=self.auth).maybe_follow()
        # Settings is not in the project navigation bar
        subnav = res.html.select('#projectSubnav')[0]
        assert_not_in('Settings', subnav.text)

    def test_sees_registration_templates(self):

        # Browse to original project
        res = self.app.get(
            '{}register/'.format(self.original.url),
            auth=self.auth
        ).maybe_follow()

        # Find registration options
        options = res.html.find('select', id='select-registration-template')\
            .find_all('option')

        # Should see number of options equal to number of registration
        # templates, plus one for "Select..."
        assert_equal(
            len(options),
            len(OSF_META_SCHEMAS) + 1
        )

        # First option should have empty value
        assert_equal(options[0].get('value'), None)

        # All registration templates should be listed in <option>s
        option_values = [
            option.get('value')
            for option in options[1:]
        ]
        for schema in OSF_META_SCHEMAS:
            assert_in(
                schema['name'],
                option_values
            )

    def test_registration_nav_not_seen(self):
        # Goes to project's page
        res = self.app.get(self.project.url, auth=self.auth).maybe_follow()
        # Settings is not in the project navigation bar
        subnav = res.html.select('#projectSubnav')[0]
        assert_not_in('Registrations', subnav.text)

class TestComponents(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory(username="test@test.com")
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)
        self.project = ProjectFactory.build(creator=self.user)
        self.project.add_contributor(contributor=self.user)
        # project has a non-registered contributor
        self.nr_user = {"nr_name": "Foo Bar", "nr_email": "foo@example.com"}
        self.project.contributor_list.append(self.nr_user)
        # A non-project componenet
        self.component = NodeFactory(
            category="hypothesis",
            creator=self.user,
            project=self.project,
        )
        self.component.save()
        self.component.set_permissions('public', self.user)
        self.component.set_permissions('private', self.user)
        self.project.save()

    def test_cannot_create_component_from_a_component(self):
        # At the component's page
        res = self.app.get(self.component.url, auth=self.auth).maybe_follow()
        assert_not_in("Add Component", res)

    def test_sees_parent(self):
        res = self.app.get(self.component.url, auth=self.auth).maybe_follow()
        parent_title = res.html.find_all('h1', class_='node-parent-title')
        assert_equal(len(parent_title), 1)
        assert_in(self.project.title, parent_title[0].text)

    def test_sees_non_registered_contributor(self):
        res = self.app.get(self.project.url, auth=self.auth).maybe_follow()
        # Sees unregeisterd user's name
        assert_in(self.nr_user['nr_name'], res)
        # Sees registred user's name
        assert_in(self.user.fullname, res)


class TestMergingAccounts(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory.build()
        self.user.set_password("science")
        self.user.save()
        self.dupe = UserFactory.build()
        self.dupe.set_password("example")
        self.dupe.save()

    def _login(self, username, password):
        '''Log in a user via at the login page.'''
        res = self.app.get("/account/").maybe_follow()
        # Fills out login info
        form = res.forms['signinForm']
        form['username'] = self.user.username
        form['password'] = 'science'
        # submits
        res = form.submit().maybe_follow()
        return res

    @unittest.skip('Disabled for now')
    def test_can_merge_accounts(self):
        res = self._login(self.user.username, "science")
        # Goes to settings
        res = self.app.get("/settings/").maybe_follow()
        # Clicks merge link
        res = res.click("Merge with duplicate account")
        # Fills out form
        form = res.forms['mergeAccountsForm']
        form['merged_username'] = self.dupe.username
        form['merged_password'] = 'example'
        form['user_password'] = 'science'
        # Submits
        res = form.submit().maybe_follow()
        # Back at the settings page
        assert_equal(res.request.path, "/settings/")
        # Sees a flash message
        assert_in("Successfully merged {0} with this account".format(self.dupe.username), res)
        # User is merged in database
        self.dupe.reload()
        assert_true(self.dupe.is_merged)

    def test_sees_error_message_when_merged_password_is_wrong(self):
        # User logs in
        res = self._login(self.user.username, "science")
        res = self.app.get("/user/merge/")
        # Fills out form
        form = res.forms['mergeAccountsForm']
        form['merged_username'] = self.dupe.username
        form['merged_password'] = 'WRONG'
        form['user_password'] = 'science'
        # Submits
        res = form.submit().maybe_follow()
        # Sees flash message
        assert_in("Could not find that user. Please check the username and password.", res)

    @unittest.skip('Disabled for now')
    def test_sees_error_message_when_own_password_is_wrong(self):
        # User logs in
        res = self._login(self.user.username, "science")
        # Goes to settings
        res = self.app.get("/settings/").maybe_follow()
        # Clicks merge link
        res = res.click("Merge with duplicate account")
        # Fills out form
        form = res.forms['mergeAccountsForm']
        form['merged_username'] = self.dupe.username
        form['merged_password'] = 'example'
        form['user_password'] = 'BAD'
        # Submits
        res = form.submit().maybe_follow()
        # Sees flash message
        assert_in("Could not authenticate. Please check your username and password.", res)

    def test_merged_user_is_not_shown_as_a_contributor(self):
        project = ProjectFactory(is_public=True)
        # Both the master and dupe are contributors
        project.add_contributor(self.dupe, log=False)
        project.add_contributor(self.user, log=False)
        project.save()
        # At the project page, both are listed as contributors
        res = self.app.get(project.url).maybe_follow()
        assert_in(self.user.fullname, res)
        assert_in(self.dupe.fullname, res)
        # The accounts are merged
        self.user.merge_user(self.dupe)
        self.user.save()
        # Now only the master user is shown at the project page
        res = self.app.get(project.url).maybe_follow()
        assert_in(self.user.fullname, res)
        assert_not_in(self.dupe.fullname, res)

    def test_merged_user_has_alert_message_on_profile(self):
        # Master merges dupe
        self.user.merge_user(self.dupe)
        self.user.save()
        # At the dupe user's profile there is an alert message at the top
        # indicating that the user is merged
        res = self.app.get("/profile/{0}/".format(self.dupe._primary_key)).maybe_follow()
        assert_in("This account has been merged", res)


# FIXME: These affect search in development environment. So need to migrate solr after running.
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


class TestShortUrls(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory(username="test@test.com")
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)
        self.project = ProjectFactory(creator=self.user)
        # A non-project componenet
        self.component = NodeFactory(category="hypothesis", creator=self.user)
        self.project.nodes.append(self.component)
        self.component.save()
        # Hack: Add some logs to component; should be unnecessary pending
        # improvements to factories from @rliebz
        self.component.set_permissions('public', user=self.user)
        self.component.set_permissions('private', user=self.user)
        self.project.save()
        self.wiki = NodeWikiFactory(user=self.user, node=self.component)

    def _url_to_body(self, url):
        return self.app.get(url, auth=self.auth).maybe_follow().normal_body

    def test_profile_url(self):
        assert_equal(
            self.app.get('/{}/'.format(self.user._primary_key)).maybe_follow().normal_body,
            self.app.get('/profile/{}/'.format(self.user._primary_key)).maybe_follow().normal_body
        )

    def test_project_url(self):
        assert_equal(
            self._url_to_body(self.project.deep_url),
            self._url_to_body(self.project.url),
        )

    def test_component_url(self):
        assert_equal(
            self._url_to_body(self.component.deep_url),
            self._url_to_body(self.component.url),
        )

    def test_file_url(self):
        node_file = self.component.add_file(self.user, None, 'test.txt',
                                         'test content', 4, 'text/plain')
        assert_equal(
            self._url_to_body(node_file.deep_url),
            self._url_to_body(node_file.url),
        )

    def test_wiki_url(self):
        assert_equal(
            self._url_to_body(self.wiki.deep_url),
            self._url_to_body(self.wiki.url),
        )


class TestPiwik(DbTestCase):
    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory()
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)
        self.user2 = UserFactory()
        api_key2 = ApiKeyFactory()
        self.user2.api_keys.append(api_key2)
        self.user2.save()
        self.auth2 = ('test', api_key2._primary_key)
        self.user3 = UserFactory()
        api_key3 = ApiKeyFactory()
        self.user3.api_keys.append(api_key3)
        self.user3.save()
        self.auth3 = ('test', api_key3._primary_key)
        self.project = ProjectFactory(creator=self.user, is_public=True)
        self.project.add_contributor(contributor=self.user)
        self.project.add_contributor(contributor=self.user2)
        self.project.save()

    def test_contains_iframe_and_src(self):
        res = self.app.get(
            "/{0}/statistics/".format(self.project._primary_key),
            auth=self.auth
        ).maybe_follow()
        assert_in("iframe", res)
        assert_in("src", res)
        assert_in('http://162.243.104.66/piwik/', res)

    def test_anymous_no_token(self):
        res = self.app.get(
            "/{0}/statistics/".format(self.project._primary_key),
            auth=self.auth3
        ).maybe_follow()
        assert_in("token_auth=anonymous", res)

    def test_contributor_token(self):
        res = self.app.get(
            "/{0}/statistics/".format(self.project._primary_key),
            auth=self.auth2
        ).maybe_follow()
        assert_in(self.user2.piwik_token, res)

    def test_no_user_token(self):
        res = self.app.get(
            "/{0}/statistics/".format(self.project._primary_key)
        ).maybe_follow()
        assert_in("token_auth=anonymous", res)

    def test_private_alert(self):
        self.project.set_permissions('private', user=self.user)
        self.project.save()
        res = self.app.get(
            "/{0}/statistics/".format(self.project._primary_key),
            auth=self.auth
        ).maybe_follow().normal_body
        print res
        assert_in(
            "Usage statistics are collected only for public resources.",
            res
        )

if __name__ == '__main__':
    unittest.main()
