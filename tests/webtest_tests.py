#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Functional tests using WebTest.'''
import unittest
import os
import re
import mock

from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp

from framework import Q
from framework.auth.model import User
from framework.auth.decorators import Auth
from tests.base import OsfTestCase, fake
from tests.factories import (UserFactory, AuthUserFactory, ProjectFactory,
                             WatchConfigFactory, NodeLogFactory, ApiKeyFactory,
                             NodeFactory, NodeWikiFactory, RegistrationFactory,
                             UnregUserFactory, UnconfirmedUserFactory)
from tests.test_features import requires_piwik
from website import settings, language
from website.project.metadata.schemas import OSF_META_SCHEMAS
from website.project.model import ensure_schemas
from website.project.views.file import get_cache_path
from website.addons.osffiles.views import get_cache_file
from framework.render.tasks import ensure_path
from website.app import init_app

app = init_app(set_backends=False, routes=True)


class TestAnUnregisteredUser(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)

    def test_can_register(self):
        # Goes to home page
        res = self.app.get('/').maybe_follow()
        # Clicks sign in button
        res = res.click('Create an Account or Sign-In').maybe_follow()
        # Fills out registration form
        form = res.forms['registerForm']
        form['register-fullname'] = 'Nicholas Cage'
        form['register-username'] = 'nickcage@example.com'
        form['register-username2'] = 'nickcage@example.com'
        form['register-password'] = 'example'
        form['register-password2'] = 'example'
        # Submits
        res = form.submit().maybe_follow()
        # There's a flash messageset
        assert_in('Registration successful. Please check nickcage@example.com '
            'to confirm your email address.', res)

    def test_sees_error_if_email_is_already_registered(self):
        # A user is already registered
        user = UserFactory(username='foo@bar.com')
        # Goes to home page
        res = self.app.get('/').maybe_follow()
        # Clicks sign in button
        res = res.click('Create an Account or Sign-In').maybe_follow()
        # Fills out registration form
        form = res.forms['registerForm']
        form['register-fullname'] = 'Foo Bar'
        form['register-username'] = 'foo@bar.com'
        form['register-username2'] = 'foo@bar.com'
        form['register-password'] = 'example'
        form['register-password2'] = 'example'
        # submits
        res = form.submit().maybe_follow()
        # sees error message because email is already registered
        assert_in('has already been registered.', res)

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


class TestAUser(OsfTestCase):

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
        res = self.app.get('/account/').maybe_follow()
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
        res = self.app.get('/account/').maybe_follow()
        # Fills the form with incorrect password
        form  = res.forms['signinForm']
        form['username'] = self.user.username
        form['password'] = 'thisiswrong'
        # Submits
        res = form.submit()
        # Sees a flash message
        assert_in('Log-in failed', res)

    def test_is_redirected_to_dashboard_already_logged_in_at_login_page(self):
        res = self._login(self.user.username, 'science')
        res = self.app.get('/login/').follow()
        assert_equal(res.request.path, '/dashboard/')

    def test_sees_projects_in_her_dashboard(self):
        # the user already has a project
        project = ProjectFactory(creator=self.user)
        project.add_contributor(self.user)
        project.save()
        # Goes to homepage, already logged in
        res = self._login(self.user.username, 'science')
        res = self.app.get('/').maybe_follow()
        # Clicks Dashboard link in navbar
        res = res.click('Dashboard', index=0)
        assert_in('Projects', res)  # Projects heading
        # The project title is listed
        assert_in(project.title, res)

    @unittest.skip("Can't test this, since logs are dynamically loaded")
    def test_sees_log_events_on_watched_projects(self):
        # Another user has a public project
        u2 = UserFactory(username='bono@u2.com', fullname='Bono')
        key = ApiKeyFactory()
        u2.api_keys.append(key)
        u2.save()
        project = ProjectFactory(creator=u2, is_public=True)
        project.add_contributor(u2)
        auth = Auth(user=u2, api_key=key)
        # A file was added to the project
        project.add_file(auth=auth, file_name='test.html',
                        content='123', size=2, content_type='text/html')
        project.save()
        # User watches the project
        watch_config = WatchConfigFactory(node=project)
        self.user.watch(watch_config)
        self.user.save()
        # Goes to her dashboard, already logged in
        res = self.app.get('/dashboard/', auth=self.auth, auto_follow=True)
        # Sees logs for the watched project
        assert_in('Watched Projects', res)  # Watched Projects header
        # The log action is in the feed
        assert_in('added file test.html', res)
        assert_in(project.title, res)

    def test_can_create_a_project(self):
        res = self._login(self.user.username, 'science')
        # Goes to dashboard (already logged in)
        res = res.click('Dashboard', index=0)
        # Clicks New Project
        res = res.click('New Project').maybe_follow()
        # Fills out the form
        form = res.forms['projectForm']
        form['title'] = 'My new project'
        form['description'] = 'Just testing'
        # Submits
        res = form.submit().maybe_follow()
        # Taken to the project's page
        assert_in('My new project', res)

    def test_sees_correct_title_home_page(self):
        # User goes to homepage
        res = self.app.get('/', auto_follow=True)
        title = res.html.title.string
        # page title is correct
        assert_equal('Open Science Framework | Home', title)

    def test_sees_correct_title_on_dashboard(self):
        # User goes to dashboard
        res = self.app.get('/dashboard/', auth=self.auth, auto_follow=True)
        title = res.html.title.string
        assert_equal('Open Science Framework | Dashboard', title)

    def test_can_see_make_public_button_if_admin(self):
        # User is a contributor on a project
        project = ProjectFactory()
        project.add_contributor(
            self.user,
            permissions=['read', 'write', 'admin'],
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_in('Make Public', res)

    def test_cant_see_make_public_button_if_not_admin(self):
        # User is a contributor on a project
        project = ProjectFactory()
        project.add_contributor(
            self.user,
            permissions=['read', 'write'],
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_not_in('Make Public', res)

    def test_can_see_make_private_button_if_admin(self):
        # User is a contributor on a project
        project = ProjectFactory(is_public=True)
        project.add_contributor(
            self.user,
            permissions=['read', 'write', 'admin'],
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_in('Make Private', res)

    def test_cant_see_make_private_button_if_not_admin(self):
        # User is a contributor on a project
        project = ProjectFactory(is_public=True)
        project.add_contributor(
            self.user,
            permissions=['read', 'write'],
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_not_in('Make Private', res)

    def test_sees_logs_on_a_project(self):
        project = ProjectFactory(is_public=True)
        # User goes to the project's page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        # Can see log event
        assert_in('created', res)

    def test_no_wiki_content_message(self):
        project = ProjectFactory(creator=self.user)
        # Goes to project's wiki, where there is no content
        res = self.app.get('/{0}/wiki/home/'.format(project._primary_key), auth=self.auth)
        # Sees a message indicating no content
        assert_in('No wiki content', res)

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


class TestRegistrations(OsfTestCase):

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
        res = self.app.get(self.project.url + 'settings/', auth=self.auth).maybe_follow()
        assert_not_in('Delete project', res)


    def test_can_see_contributor(self):
        # Goes to project's page
        res = self.app.get(self.project.url, auth=self.auth).maybe_follow()
        # Settings is not in the project navigation bar
        subnav = res.html.select('#projectSubnav')[0]
        assert_in('Contributors', subnav.text)

    def test_sees_registration_templates(self):

        # Browse to original project
        res = self.app.get(
            '{}register/'.format(self.original.url),
            auth=self.auth
        ).maybe_follow()

        # Find registration options
        options = res.html.find(
            'select', id='select-registration-template'
        ).find_all('option')

        # Should see number of options equal to number of registration
        # templates, plus one for 'Select...'
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


class TestComponents(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(contributor=self.user, auth=self.consolidate_auth)
        # A non-project componenet
        self.component = NodeFactory(
            category='hypothesis',
            creator=self.user,
            project=self.project,
        )
        self.component.save()
        self.component.set_privacy('public', self.consolidate_auth)
        self.component.set_privacy('private', self.consolidate_auth)
        self.project.save()

    def test_can_create_component_from_a_project(self):
        res = self.app.get(self.project.url, auth=self.user.auth).maybe_follow()
        assert_in('Add Component', res)

    def test_cannot_create_component_from_a_component(self):
        res = self.app.get(self.component.url, auth=self.user.auth).maybe_follow()
        assert_not_in('Add Component', res)

    def test_sees_parent(self):
        res = self.app.get(self.component.url, auth=self.user.auth).maybe_follow()
        parent_title = res.html.find_all('h1', class_='node-parent-title')
        assert_equal(len(parent_title), 1)
        assert_in(self.project.title, parent_title[0].text)

    def test_delete_project(self):
        res = self.app.get(
            self.component.url + 'settings/',
            auth=self.user.auth
        ).maybe_follow()
        assert_in(
            'Delete {0}'.format(self.component.project_or_component),
            res
        )

    def test_cant_delete_project_if_not_admin(self):
        non_admin = AuthUserFactory()
        self.component.add_contributor(
            non_admin,
            permissions=['read', 'write'],
            auth=self.consolidate_auth,
            save=True,
        )
        res = self.app.get(
            self.component.url + 'settings/',
            auth=non_admin.auth
        ).maybe_follow()
        assert_not_in(
            'Delete {0}'.format(self.component.project_or_component),
            res
        )


class TestMergingAccounts(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory.build()
        self.user.set_password('science')
        self.user.save()
        self.dupe = UserFactory.build()
        self.dupe.set_password('example')
        self.dupe.save()

    def _login(self, username, password):
        '''Log in a user via at the login page.'''
        res = self.app.get('/account/').maybe_follow()
        # Fills out login info
        form = res.forms['signinForm']
        form['username'] = self.user.username
        form['password'] = 'science'
        # submits
        res = form.submit().maybe_follow()
        return res

    @unittest.skip('Disabled for now')
    def test_can_merge_accounts(self):
        res = self._login(self.user.username, 'science')
        # Goes to settings
        res = self.app.get('/settings/').maybe_follow()
        # Clicks merge link
        res = res.click('Merge with duplicate account')
        # Fills out form
        form = res.forms['mergeAccountsForm']
        form['merged_username'] = self.dupe.username
        form['merged_password'] = 'example'
        form['user_password'] = 'science'
        # Submits
        res = form.submit().maybe_follow()
        # Back at the settings page
        assert_equal(res.request.path, '/settings/')
        # Sees a flash message
        assert_in('Successfully merged {0} with this account'.format(self.dupe.username), res)
        # User is merged in database
        self.dupe.reload()
        assert_true(self.dupe.is_merged)

    def test_sees_error_message_when_merged_password_is_wrong(self):
        # User logs in
        res = self._login(self.user.username, 'science')
        res = self.app.get('/user/merge/')
        # Fills out form
        form = res.forms['mergeAccountsForm']
        form['merged_username'] = self.dupe.username
        form['merged_password'] = 'WRONG'
        form['user_password'] = 'science'
        # Submits
        res = form.submit().maybe_follow()
        # Sees flash message
        assert_in('Could not find that user. Please check the username and password.', res)

    @unittest.skip('Disabled for now')
    def test_sees_error_message_when_own_password_is_wrong(self):
        # User logs in
        res = self._login(self.user.username, 'science')
        # Goes to settings
        res = self.app.get('/settings/').maybe_follow()
        # Clicks merge link
        res = res.click('Merge with duplicate account')
        # Fills out form
        form = res.forms['mergeAccountsForm']
        form['merged_username'] = self.dupe.username
        form['merged_password'] = 'example'
        form['user_password'] = 'BAD'
        # Submits
        res = form.submit().maybe_follow()
        # Sees flash message
        assert_in('Could not authenticate. Please check your username and password.', res)

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
        assert_true(self.dupe.is_merged)
        assert_not_in(self.dupe.fullname, res)

    def test_merged_user_has_alert_message_on_profile(self):
        # Master merges dupe
        self.user.merge_user(self.dupe)
        self.user.save()
        # At the dupe user's profile there is an alert message at the top
        # indicating that the user is merged
        res = self.app.get('/profile/{0}/'.format(self.dupe._primary_key)).maybe_follow()
        assert_in('This account has been merged', res)


# FIXME: These affect search in development environment. So need to migrate solr after running.
# # Remove this side effect.
@unittest.skipIf(not settings.USE_SOLR, 'Skipping because USE_SOLR is False')
class TestSearching(OsfTestCase):

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
        res = self.app.get('/').maybe_follow()
        # Fills search form
        form = res.forms['searchBar']
        form['q'] = user.fullname
        res = form.submit().maybe_follow()
        # No results, so clicks Search Users
        res = res.click('Search users')
        # The username shows as a search result
        assert_in(user.fullname, res)

    def test_a_public_project_from_home_page(self):
        project = ProjectFactory(title='Foobar Project', is_public=True)
        # Searches a part of the name
        res = self.app.get('/').maybe_follow()
        project.reload()
        form = res.forms['searchBar']
        form['q'] = 'Foobar'
        res = form.submit().maybe_follow()
        # A link to the project is shown as a result
        assert_in('Foobar Project', res)


class TestShortUrls(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory()
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', api_key._primary_key)
        self.consolidate_auth=Auth(user=self.user, api_key=api_key)
        self.project = ProjectFactory(creator=self.user)
        # A non-project componenet
        self.component = NodeFactory(category='hypothesis', creator=self.user)
        self.project.nodes.append(self.component)
        self.component.save()
        # Hack: Add some logs to component; should be unnecessary pending
        # improvements to factories from @rliebz
        self.component.set_privacy('public', auth=self.consolidate_auth)
        self.component.set_privacy('private', auth=self.consolidate_auth)
        self.wiki = NodeWikiFactory(user=self.user, node=self.component)

    def _url_to_body(self, url):
        return self.app.get(url, auth=self.auth).maybe_follow().normal_body

    def test_profile_url(self):
        res1 = self.app.get('/{}/'.format(self.user._primary_key)).maybe_follow()
        res2 = self.app.get('/profile/{}/'.format(self.user._primary_key)).maybe_follow()
        assert_equal(
            res1.normal_body,
            res2.normal_body
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

    def _mock_rendered_file(self, component, fobj):
        node_settings = component.get_addon('osffiles')
        cache_dir = get_cache_path(node_settings)
        cache_file = get_cache_file(fobj.filename, fobj.latest_version_number(component))
        cache_file_path = os.path.join(cache_dir, cache_file)
        ensure_path(cache_dir)
        with open(cache_file_path, 'w') as fp:
            fp.write('test content')

    def test_file_url(self):
        node_file = self.component.add_file(
            self.consolidate_auth, 'test.txt',
            'test content', 4, 'text/plain'
        )
        self._mock_rendered_file(self.component, node_file)
        # Warm up to account for file rendering
        _ = self._url_to_body(node_file.url(self.component))
        assert_equal(
            self._url_to_body(node_file.deep_url(self.component)),
            self._url_to_body(node_file.url(self.component)),
        )

    def test_wiki_url(self):
        assert_equal(
            self._url_to_body(self.wiki.deep_url),
            self._url_to_body(self.wiki.url),
        )


@requires_piwik
class TestPiwik(OsfTestCase):
    def setUp(self):
        self.app = TestApp(app)
        self.users = [
            AuthUserFactory()
            for _ in range(3)
        ]
        self.consolidate_auth = Auth(user=self.users[0])
        self.project = ProjectFactory(creator=self.users[0], is_public=True)
        self.project.add_contributor(contributor=self.users[1])
        self.project.save()

    def test_contains_iframe_and_src(self):
        res = self.app.get(
            '/{0}/statistics/'.format(self.project._primary_key),
            auth=self.users[0].auth
        ).maybe_follow()
        assert_in('iframe', res)
        assert_in('src', res)
        assert_in('http://162.243.104.66/piwik/', res)

    def test_anonymous_no_token(self):
        res = self.app.get(
            '/{0}/statistics/'.format(self.project._primary_key),
            auth=self.users[2].auth
        ).maybe_follow()
        assert_in('token_auth=anonymous', res)

    def test_contributor_token(self):
        res = self.app.get(
            '/{0}/statistics/'.format(self.project._primary_key),
            auth=self.users[1].auth
        ).maybe_follow()
        assert_in(self.users[1].piwik_token, res)

    def test_no_user_token(self):
        res = self.app.get(
            '/{0}/statistics/'.format(self.project._primary_key)
        ).maybe_follow()
        assert_in('token_auth=anonymous', res)

    def test_private_alert(self):
        self.project.set_privacy('private', auth=self.consolidate_auth)
        self.project.save()
        res = self.app.get(
            '/{0}/statistics/'.format(self.project._primary_key),
            auth=self.users[0].auth
        ).maybe_follow().normal_body
        assert_in(
            'Usage statistics are collected only for public resources.',
            res
        )

@unittest.skipIf(not settings.ALLOW_CLAIMING, 'skipping until claiming is fully implemented')
class TestClaiming(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)

    def test_correct_name_shows_in_contributor_list(self):
        name1, email = fake.name(), fake.email()
        UnregUserFactory(fullname=name1, email=email)
        name2, email = fake.name(), fake.email()
        # Added with different name
        self.project.add_unregistered_contributor(fullname=name2,
            email=email, auth=Auth(self.referrer))
        self.project.save()

        res = self.app.get(self.project.url, auth=self.referrer.auth)
        # Correct name is shown
        assert_in(name2, res)
        assert_not_in(name1, res)


    def test_user_can_set_password_on_claim_page(self):
        name, email = fake.name(), fake.email()
        new_user = self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        self.project.reload()
        assert_in('Set Password', res)
        form = res.forms['setPasswordForm']
        form['username'] = new_user.username
        form['password'] = 'killerqueen'
        form['password2'] = 'killerqueen'
        res = form.submit().maybe_follow()
        new_user.reload()
        # at settings page
        assert_equal(res.request.path, '/settings/')
        assert_in('Welcome to the OSF', res)

    def test_sees_is_redirected_if_user_already_logged_in(self):
        name, email = fake.name(), fake.email()
        new_user = self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        existing = AuthUserFactory()
        claim_url = new_user.get_claim_url(self.project._primary_key)
        # a user is already logged in
        res = self.app.get(claim_url, auth=existing.auth, expect_errors=True)
        assert_equal(res.status_code, 302)

    def test_unregistered_users_names_are_project_specific(self):
        name1, name2, email = fake.name(), fake.name(), fake.email()
        project2 = ProjectFactory(creator=self.referrer)
        # different projects use different names for the same unreg contributor
        self.project.add_unregistered_contributor(
            email=email,
            fullname=name1,
            auth=Auth(self.referrer)
        )
        self.project.save()
        project2.add_unregistered_contributor(
            email=email,
            fullname=name2,
            auth=Auth(self.referrer)
        )
        project2.save()
        self.app.authenticate(*self.referrer.auth)
        # Each project displays a different name in the contributor list
        res = self.app.get(self.project.url)
        assert_in(name1, res)

        res2 = self.app.get(project2.url)
        assert_in(name2, res2)

    def test_unregistered_user_can_create_an_account(self):
        # User is added as an unregistered contributor to a project
        email, name = fake.email(), fake.name()
        self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        # Goes to registration page (instead of claiming their email)
        res = self.app.get('/account/').maybe_follow()
        form = res.forms['registerForm']
        form['register-fullname'] = name
        form['register-username'] = email
        form['register-username2'] = email
        form['register-password'] = 'example'
        form['register-password2'] = 'example'
        res = form.submit()
        # registered successfully
        assert_in(language.REGISTRATION_SUCCESS.format(email=email), res)

    def test_cannot_go_to_claim_url_after_setting_password(self):
        name, email = fake.name(), fake.email()
        new_user = self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        # Goes to claim url and successfully claims account
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        self.project.reload()
        assert_in('Set Password', res)
        form = res.forms['setPasswordForm']
        form['username'] = new_user.username
        form['password'] = 'killerqueen'
        form['password2'] = 'killerqueen'
        res = form.submit().maybe_follow()

        # logs out
        res = self.app.get('/logout/').maybe_follow()
        # tries to go to claim url again
        res = self.app.get(claim_url, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('already been claimed', res)

    def test_cannot_set_email_to_a_user_that_already_exists(self):
        reg_user = UserFactory()
        name, email = fake.name(), fake.email()
        new_user = self.project.add_unregistered_contributor(
            email=email,
            fullname=name,
            auth=Auth(self.referrer)
        )
        self.project.save()
        # Goes to claim url and successfully claims account
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        self.project.reload()
        assert_in('Set Password', res)
        form = res.forms['setPasswordForm']
        # Fills out an email that is the username of another user
        form['username'] = reg_user.username
        form['password'] = 'killerqueen'
        form['password2'] = 'killerqueen'
        res = form.submit().maybe_follow(expect_errors=True)
        assert_in(language.ALREADY_REGISTERED.format(email=reg_user.username), res)

    def test_correct_display_name_is_shown_at_claim_page(self):
        original_name = fake.name()
        unreg = UnregUserFactory(fullname=original_name)

        different_name= fake.name()
        new_user = self.project.add_unregistered_contributor(email=unreg.username,
            fullname=different_name,
            auth=Auth(self.referrer))
        self.project.save()
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        # Correct name (different_name) should be on page
        assert_in(different_name, res)


class TestConfirmingEmail(OsfTestCase):
    def setUp(self):
        self.app = TestApp(app)
        self.user = UnconfirmedUserFactory()
        self.confirmation_url = self.user.get_confirmation_url(self.user.username,
            external=False)
        self.confirmation_token = self.user.get_confirmation_token(self.user.username)

    def test_redirects_to_settings(self):
        res = self.app.get(self.confirmation_url).follow()
        assert_equal(res.request.path, '/settings/', 'redirected to settings page')
        assert_in('Welcome to the OSF!', res, 'shows flash message')
        assert_in('Please update the following settings.', res)

    def test_error_page_if_confirm_link_is_expired(self):
        self.user.confirm_email(self.confirmation_token)
        self.user.save()
        res = self.app.get(self.confirmation_url, expect_errors=True)
        assert_in('Link Expired', res)

    def test_sees_flash_message_if_email_unconfirmed(self):
        # set a password for user
        self.user.set_password('bicycle')
        self.user.save()
        # Goes to log in page
        res = self.app.get('/account/').maybe_follow()
        # Fills the form with incorrect password
        form  = res.forms['signinForm']
        form['username'] = self.user.username
        form['password'] = 'bicycle'
        res = form.submit().maybe_follow()
        assert_in(language.UNCONFIRMED, res, 'shows flash message')
        # clicks on resend link in flash message
        res = res.click('Click here')
        assert_equal(res.request.path, '/resend/', 'at resend page')


    @mock.patch('framework.auth.views.send_confirm_email')
    def test_resend_form(self, send_confirm_email):
        res = self.app.get('/resend/')
        form = res.forms['resendForm']
        form['email'] = self.user.username
        res = form.submit()
        assert_true(send_confirm_email.called)
        assert_in('Resent email to', res)

    def test_resend_form_does_nothing_if_not_in_db(self):
        res = self.app.get('/resend/')
        form = res.forms['resendForm']
        form['email'] = 'nowheretobefound@foo.com'
        res = form.submit()
        assert_equal(res.request.path, '/resend/')

    def test_resend_form_shows_alert_if_email_already_confirmed(self):
        user = UnconfirmedUserFactory()
        url = user.get_confirmation_url(user.username, external=False)
        # User confirms their email address
        self.app.get(url).maybe_follow()
        # tries to resend confirmation
        res = self.app.get('/resend/')
        form = res.forms['resendForm']
        form['email'] = user.username
        res = form.submit()
        # Sees alert message
        assert_in('already been confirmed', res)

class TestClaimingAsARegisteredUser(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        name, email = fake.name(), fake.email()
        self.user = self.project.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

    @mock.patch('website.project.views.contributor.session')
    def test_user_with_claim_url_registers_new_account(self, mock_session):
        # Assume that the unregistered user data is already stored in the session
        mock_session.data = {
            'unreg_user': {
                'uid': self.user._primary_key,
                'pid': self.project._primary_key,
                'token': self.user.get_unclaimed_record(
                    self.project._primary_key)['token']
            }
        }
        res2 = self.app.get('/account/')
        # Fills in Register form
        form = res2.forms['registerForm']
        form['register-fullname'] = 'tester'
        form['register-username'] = 'test@test.com'
        form['register-username2'] = 'test@test.com'
        form['register-password'] = 'testing'
        form['register-password2'] = 'testing'
        res3 = form.submit()

        assert_in('Registration successful.', res3.body)
        assert_in('Successfully claimed contributor', res3.body)

        u = User.find(Q('username', 'eq', 'test@test.com'))[0]
        key = ApiKeyFactory()
        u.api_keys.append(key)
        u.save()
        u.auth = ('test', key._primary_key)
        self.app.get(u.get_confirmation_url('test@test.com')).follow(auth=u.auth)
        # Confirms their email address
        self.project.reload()
        self.user.reload()
        u.reload()
        assert_not_in(self.user._primary_key, self.project.contributors)
        assert_equal(2, len(self.project.contributors))
        # user is now a contributor to self.project
        assert_in(u._primary_key, self.project.contributors)

    @mock.patch('website.project.views.contributor.session')
    def test_user_can_log_in_with_a_different_account(self, mock_session):
        # Assume that the unregistered user data is already stored in the session
        mock_session.data = {
            'unreg_user': {
                'uid': self.user._primary_key,
                'pid': self.project._primary_key,
                'token': self.user.get_unclaimed_record(
                    self.project._primary_key)['token']
            }
        }
        right_user = AuthUserFactory.build(fullname="Right User")
        right_user.set_password('science')
        right_user.save()
        # User goes to the claim page, but a different user (lab_user) is logged in
        lab_user = AuthUserFactory(fullname="Lab Comp")

        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=lab_user.auth).follow(auth=lab_user.auth)

        # verify that the "Claim Account" form is returned
        assert_in('Claim Contributor', res.body)

        # Clicks "I am not Lab Comp"
        # Taken to login/register page

        res2 = res.click(linkid='signOutLink')
        # Fills in log in form
        form = res2.forms['signinForm']
        form['username'] = right_user.username
        form['password'] = 'science'
        # submits
        res3 = form.submit().follow()

        # Back at claim contributor page
        assert_in('Claim Contributor', res3)
        # Verifies their password
        form = res3.forms['claimContributorForm']
        form['password'] = 'science'
        form.submit()

        self.project.reload()
        right_user.reload()
        self.user.reload()
        # user is now a contributor to self.project
        assert_in(right_user._primary_key, self.project.contributors)

        # lab user is not a contributor
        assert_not_in(lab_user._primary_key, self.project.contributors)

    def test_claim_user_registered_with_correct_password(self):
        reg_user = AuthUserFactory()
        reg_user.set_password('killerqueen')
        reg_user.save()
        url = self.user.get_claim_url(self.project._primary_key)
        # Follow to password re-enter page
        res = self.app.get(url, auth=reg_user.auth).follow(auth=reg_user.auth)

        # verify that the "Claim Account" form is returned
        assert_in('Claim Contributor', res.body)

        form = res.forms['claimContributorForm']
        form['password'] = 'killerqueen'
        res = form.submit(auth=reg_user.auth).follow(auth=reg_user.auth)


        self.project.reload()
        self.user.reload()
        # user is now a contributor to the project
        assert_in(reg_user._primary_key, self.project.contributors)

        # the unregistered user (self.user) is removed as a contributor, and their
        assert_not_in(self.user._primary_key, self.project.contributors)

        # unclaimed record for the project has been deleted
        assert_not_in(self.project._primary_key, self.user.unclaimed_records)


if __name__ == '__main__':
    unittest.main()
