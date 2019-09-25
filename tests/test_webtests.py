#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functional tests using WebTest."""
import datetime as dt
from rest_framework import status as http_status
import logging
import unittest

import markupsafe
import mock
import pytest
from nose.tools import *  # noqa: F403
import re

from django.utils import timezone
from addons.wiki.utils import to_mongo_key
from framework.auth import exceptions as auth_exc
from framework.auth.core import Auth
from tests.base import OsfTestCase
from tests.base import fake
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    NodeFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PrivateLinkFactory,
    ProjectFactory,
    RegistrationFactory,
    SubjectFactory,
    UserFactory,
    UnconfirmedUserFactory,
    UnregUserFactory,
)
from osf.utils import permissions
from addons.wiki.models import WikiPage, WikiVersion
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from website import settings, language
from addons.osfstorage.models import OsfStorageFile
from website.util import web_url_for, api_url_for

from api_tests import utils as test_utils

logging.getLogger('website.project.model').setLevel(logging.ERROR)


def assert_in_html(member, container, **kwargs):
    """Looks for the specified member in markupsafe-escaped HTML output"""
    member = markupsafe.escape(member)
    return assert_in(member, container, **kwargs)


def assert_not_in_html(member, container, **kwargs):
    """Looks for the specified member in markupsafe-escaped HTML output"""
    member = markupsafe.escape(member)
    return assert_not_in(member, container, **kwargs)


class TestDisabledUser(OsfTestCase):

    def setUp(self):
        super(TestDisabledUser, self).setUp()
        self.user = UserFactory()
        self.user.set_password('Korben Dallas')
        self.user.is_disabled = True
        self.user.save()

    def test_profile_disabled_returns_401(self):
        res = self.app.get(self.user.url, expect_errors=True)
        assert_equal(res.status_code, 410)


class TestAnUnregisteredUser(OsfTestCase):

    def test_cant_see_profile_if_not_logged_in(self):
        url = web_url_for('profile_view')
        res = self.app.get(url)
        res = res.follow()
        assert_equal(res.status_code, 301)
        assert_in('/login/', res.headers['Location'])


@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_quickfiles_creation
class TestAUser(OsfTestCase):

    def setUp(self):
        super(TestAUser, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    def test_can_see_profile_url(self):
        res = self.app.get(self.user.url).maybe_follow()
        assert_in(self.user.url, res)

    # `GET /login/` without parameters is redirected to `/dashboard/` page which has `@must_be_logged_in` decorator
    # if user is not logged in, she/he is further redirected to CAS login page
    def test_is_redirected_to_cas_if_not_logged_in_at_login_page(self):
        res = self.app.get('/login/').follow()
        assert_equal(res.status_code, 302)
        location = res.headers.get('Location')
        assert_in('login?service=', location)

    def test_is_redirected_to_dashboard_if_already_logged_in_at_login_page(self):
        res = self.app.get('/login/', auth=self.user.auth)
        assert_equal(res.status_code, 302)
        assert 'dashboard' in res.headers.get('Location')

    def test_register_page(self):
        res = self.app.get('/register/')
        assert_equal(res.status_code, 200)

    def test_is_redirected_to_dashboard_if_already_logged_in_at_register_page(self):
        res = self.app.get('/register/', auth=self.user.auth)
        assert_equal(res.status_code, 302)
        assert 'dashboard' in res.headers.get('Location')

    def test_sees_projects_in_her_dashboard(self):
        # the user already has a project
        project = ProjectFactory(creator=self.user)
        project.add_contributor(self.user)
        project.save()
        res = self.app.get('/myprojects/', auth=self.user.auth)
        assert_in('Projects', res)  # Projects heading

    def test_does_not_see_osffiles_in_user_addon_settings(self):
        res = self.app.get('/settings/addons/', auth=self.auth, auto_follow=True)
        assert_not_in('OSF Storage', res)

    def test_sees_osffiles_in_project_addon_settings(self):
        project = ProjectFactory(creator=self.user)
        project.add_contributor(
            self.user,
            permissions=permissions.ADMIN,
            save=True)
        res = self.app.get('/{0}/addons/'.format(project._primary_key), auth=self.auth, auto_follow=True)
        assert_in('OSF Storage', res)

    def test_sees_correct_title_on_dashboard(self):
        # User goes to dashboard
        res = self.app.get('/myprojects/', auth=self.auth, auto_follow=True)
        title = res.html.title.string
        assert_equal('OSF | My Projects', title)

    def test_can_see_make_public_button_if_admin(self):
        # User is a contributor on a project
        project = ProjectFactory()
        project.add_contributor(
            self.user,
            permissions=permissions.ADMIN,
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_in('Make Public', res)

    def test_cant_see_make_public_button_if_not_admin(self):
        # User is a contributor on a project
        project = ProjectFactory()
        project.add_contributor(
            self.user,
            permissions=permissions.WRITE,
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_not_in('Make Public', res)

    def test_can_see_make_private_button_if_admin(self):
        # User is a contributor on a project
        project = ProjectFactory(is_public=True)
        project.add_contributor(
            self.user,
            permissions=permissions.ADMIN,
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth).maybe_follow()
        assert_in('Make Private', res)

    def test_cant_see_make_private_button_if_not_admin(self):
        # User is a contributor on a project
        project = ProjectFactory(is_public=True)
        project.add_contributor(
            self.user,
            permissions=permissions.WRITE,
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
        assert_in('Add important information, links, or images here to describe your project.', res)
        # Sees that edit panel is open by default when home wiki has no content
        assert_in('panelsUsed: ["view", "menu", "edit"]', res)

    def test_wiki_content(self):
        project = ProjectFactory(creator=self.user)
        wiki_page_name = 'home'
        wiki_content = 'Kittens'
        wiki_page = WikiFactory(
            user=self.user,
            node=project,
        )
        wiki = WikiVersionFactory(
            wiki_page=wiki_page,
            content=wiki_content
        )
        res = self.app.get('/{0}/wiki/{1}/'.format(
            project._primary_key,
            wiki_page_name,
        ), auth=self.auth)
        assert_not_in('Add important information, links, or images here to describe your project.', res)
        assert_in(wiki_content, res)
        assert_in('panelsUsed: ["view", "menu"]', res)

    def test_wiki_page_name_non_ascii(self):
        project = ProjectFactory(creator=self.user)
        non_ascii = to_mongo_key('WöRlÐé')
        WikiPage.objects.create_for_node(project, 'WöRlÐé', 'new content', Auth(self.user))
        wv = WikiVersion.objects.get_for_node(project, non_ascii)
        assert wv.wiki_page.page_name.upper() == non_ascii.decode('utf-8').upper()

    def test_noncontributor_cannot_see_wiki_if_no_content(self):
        user2 = UserFactory()
        # user2 creates a public project and adds no wiki content
        project = ProjectFactory(creator=user2, is_public=True)
        # self navigates to project
        res = self.app.get(project.url).maybe_follow()
        # Should not see wiki widget (since non-contributor and no content)
        assert_not_in('Add important information, links, or images here to describe your project.', res)

    def test_wiki_does_not_exist(self):
        project = ProjectFactory(creator=self.user)
        res = self.app.get('/{0}/wiki/{1}/'.format(
            project._primary_key,
            'not a real page yet',
        ), auth=self.auth, expect_errors=True)
        assert_in('Add important information, links, or images here to describe your project.', res)

    def test_sees_own_profile(self):
        res = self.app.get('/profile/', auth=self.auth)
        td1 = res.html.find('td', text=re.compile(r'Public(.*?)Profile'))
        td2 = td1.find_next_sibling('td')
        assert_equal(td2.text, self.user.display_absolute_url)

    def test_sees_another_profile(self):
        user2 = UserFactory()
        res = self.app.get(user2.url, auth=self.auth)
        td1 = res.html.find('td', text=re.compile(r'Public(.*?)Profile'))
        td2 = td1.find_next_sibling('td')
        assert_equal(td2.text, user2.display_absolute_url)


@pytest.mark.enable_bookmark_creation
class TestComponents(OsfTestCase):

    def setUp(self):
        super(TestComponents, self).setUp()
        self.user = AuthUserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.project.add_contributor(contributor=self.user, auth=self.consolidate_auth)
        # A non-project componenet
        self.component = NodeFactory(
            category='hypothesis',
            creator=self.user,
            parent=self.project,
        )
        self.component.save()
        self.component.set_privacy('public', self.consolidate_auth)
        self.component.set_privacy('private', self.consolidate_auth)
        self.project.save()
        self.project_url = self.project.web_url_for('view_project')

    def test_sees_parent(self):
        res = self.app.get(self.component.url, auth=self.user.auth).maybe_follow()
        parent_title = res.html.find_all('h2', class_='node-parent-title')
        assert_equal(len(parent_title), 1)
        assert_in(self.project.title, parent_title[0].text)  # Bs4 will handle unescaping HTML here

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
            permissions=permissions.WRITE,
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

    def test_can_configure_comments_if_admin(self):
        res = self.app.get(
            self.component.url + 'settings/',
            auth=self.user.auth,
        ).maybe_follow()
        assert_in('Commenting', res)

    def test_cant_configure_comments_if_not_admin(self):
        non_admin = AuthUserFactory()
        self.component.add_contributor(
            non_admin,
            permissions=permissions.WRITE,
            auth=self.consolidate_auth,
            save=True,
        )
        res = self.app.get(
            self.component.url + 'settings/',
            auth=non_admin.auth
        ).maybe_follow()
        assert_not_in('Commenting', res)

    def test_components_should_have_component_list(self):
        res = self.app.get(self.component.url, auth=self.user.auth)
        assert_in('Components', res)


@pytest.mark.enable_bookmark_creation
class TestPrivateLinkView(OsfTestCase):

    def setUp(self):
        super(TestPrivateLinkView, self).setUp()
        self.user = AuthUserFactory()  # Is NOT a contributor
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory(anonymous=True)
        self.link.nodes.add(self.project)
        self.link.save()
        self.project_url = self.project.web_url_for('view_project')

    def test_anonymous_link_hide_contributor(self):
        res = self.app.get(self.project_url, {'view_only': self.link.key})
        assert_in('Anonymous Contributors', res.body)
        assert_not_in(self.user.fullname, res)

    def test_anonymous_link_hides_citations(self):
        res = self.app.get(self.project_url, {'view_only': self.link.key})
        assert_not_in('Citation:', res)

    def test_no_warning_for_read_only_user_with_valid_link(self):
        link2 = PrivateLinkFactory(anonymous=False)
        link2.nodes.add(self.project)
        link2.save()
        self.project.add_contributor(
            self.user,
            permissions=permissions.READ,
            save=True,
        )
        res = self.app.get(self.project_url, {'view_only': link2.key},
                           auth=self.user.auth)
        assert_not_in(
            'is being viewed through a private, view-only link. '
            'Anyone with the link can view this project. Keep '
            'the link safe.',
            res.body
        )

    def test_no_warning_for_read_only_user_with_invalid_link(self):
        self.project.add_contributor(
            self.user,
            permissions=permissions.READ,
            save=True,
        )
        res = self.app.get(self.project_url, {'view_only': 'not_valid'},
                           auth=self.user.auth)
        assert_not_in(
            'is being viewed through a private, view-only link. '
            'Anyone with the link can view this project. Keep '
            'the link safe.',
            res.body
        )


@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_quickfiles_creation
class TestMergingAccounts(OsfTestCase):

    def setUp(self):
        super(TestMergingAccounts, self).setUp()
        self.user = UserFactory.build()
        self.user.fullname = "tess' test string"
        self.user.set_password('science')
        self.user.save()
        self.dupe = UserFactory.build()
        self.dupe.set_password('example')
        self.dupe.save()

    def test_merged_user_is_not_shown_as_a_contributor(self):
        project = ProjectFactory(is_public=True)
        # Both the master and dupe are contributors
        project.add_contributor(self.dupe, log=False)
        project.add_contributor(self.user, log=False)
        project.save()
        # At the project page, both are listed as contributors
        res = self.app.get(project.url).maybe_follow()
        assert_in_html(self.user.fullname, res)
        assert_in_html(self.dupe.fullname, res)
        # The accounts are merged
        self.user.merge_user(self.dupe)
        self.user.save()
        # Now only the master user is shown at the project page
        res = self.app.get(project.url).maybe_follow()
        assert_in_html(self.user.fullname, res)
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


@pytest.mark.enable_bookmark_creation
class TestShortUrls(OsfTestCase):

    def setUp(self):
        super(TestShortUrls, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        # A non-project componenet
        self.component = NodeFactory(parent=self.project, category='hypothesis', creator=self.user)
        # Hack: Add some logs to component; should be unnecessary pending
        # improvements to factories from @rliebz
        self.component.set_privacy('public', auth=self.consolidate_auth)
        self.component.set_privacy('private', auth=self.consolidate_auth)
        self.wiki = WikiFactory(
            user=self.user,
            node=self.component,
        )

    def _url_to_body(self, url):
        return self.app.get(
            url,
            auth=self.auth
        ).maybe_follow(
            auth=self.auth,
        ).normal_body

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

    def test_wiki_url(self):
        assert_equal(
            self._url_to_body(self.wiki.deep_url),
            self._url_to_body(self.wiki.url),
        )


@pytest.mark.enable_bookmark_creation
@pytest.mark.enable_implicit_clean
class TestClaiming(OsfTestCase):

    def setUp(self):
        super(TestClaiming, self).setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)

    def test_correct_name_shows_in_contributor_list(self):
        name1, email = fake.name(), fake_email()
        UnregUserFactory(fullname=name1, email=email)
        name2, email = fake.name(), fake_email()
        # Added with different name
        self.project.add_unregistered_contributor(fullname=name2,
            email=email, auth=Auth(self.referrer))
        self.project.save()

        res = self.app.get(self.project.url, auth=self.referrer.auth)
        # Correct name is shown
        assert_in_html(name2, res)
        assert_not_in(name1, res)

    def test_user_can_set_password_on_claim_page(self):
        name, email = fake.name(), fake_email()
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
        #form['username'] = new_user.username #Removed as long as E-mail can't be updated.
        form['password'] = 'killerqueen'
        form['password2'] = 'killerqueen'
        res = form.submit().follow()
        new_user.reload()
        assert_true(new_user.check_password('killerqueen'))

    def test_sees_is_redirected_if_user_already_logged_in(self):
        name, email = fake.name(), fake_email()
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
        name1, name2, email = fake.name(), fake.name(), fake_email()
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
        assert_in_html(name1, res)

        res2 = self.app.get(project2.url)
        assert_in_html(name2, res2)

    @unittest.skip('as long as E-mails cannot be changed')
    def test_cannot_set_email_to_a_user_that_already_exists(self):
        reg_user = UserFactory()
        name, email = fake.name(), fake_email()
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
        assert_in(
            language.ALREADY_REGISTERED.format(email=reg_user.username),
            res
        )

    def test_correct_display_name_is_shown_at_claim_page(self):
        original_name = fake.name()
        unreg = UnregUserFactory(fullname=original_name)

        different_name = fake.name()
        new_user = self.project.add_unregistered_contributor(
            email=unreg.username,
            fullname=different_name,
            auth=Auth(self.referrer),
        )
        self.project.save()
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.get(claim_url)
        # Correct name (different_name) should be on page
        assert_in_html(different_name, res)


class TestConfirmingEmail(OsfTestCase):

    def setUp(self):
        super(TestConfirmingEmail, self).setUp()
        self.user = UnconfirmedUserFactory()
        self.confirmation_url = self.user.get_confirmation_url(
            self.user.username,
            external=False,
        )
        self.confirmation_token = self.user.get_confirmation_token(
            self.user.username
        )

    def test_cannot_remove_another_user_email(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        url = api_url_for('update_user')
        header = {'id': user1.username, 'emails': [{'address': user1.username}]}
        res = self.app.put_json(url, header, auth=user2.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_cannnot_make_primary_email_for_another_user(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        email = 'test@cos.io'
        user1.emails.create(address=email)
        user1.save()
        url = api_url_for('update_user')
        header = {'id': user1.username,
                  'emails': [{'address': user1.username, 'primary': False, 'confirmed': True},
                            {'address': email, 'primary': True, 'confirmed': True}
                  ]}
        res = self.app.put_json(url, header, auth=user2.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_cannnot_add_email_for_another_user(self):
        user1 = AuthUserFactory()
        user2 = AuthUserFactory()
        email = 'test@cos.io'
        url = api_url_for('update_user')
        header = {'id': user1.username,
                  'emails': [{'address': user1.username, 'primary': True, 'confirmed': True},
                            {'address': email, 'primary': False, 'confirmed': False}
                  ]}
        res = self.app.put_json(url, header, auth=user2.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_error_page_if_confirm_link_is_used(self):
        self.user.confirm_email(self.confirmation_token)
        self.user.save()
        res = self.app.get(self.confirmation_url, expect_errors=True)

        assert_in(auth_exc.InvalidTokenError.message_short, res)
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)


@pytest.mark.enable_implicit_clean
@pytest.mark.enable_bookmark_creation
class TestClaimingAsARegisteredUser(OsfTestCase):

    def setUp(self):
        super(TestClaimingAsARegisteredUser, self).setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        name, email = fake.name(), fake_email()
        self.user = self.project.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

    def test_claim_user_registered_with_correct_password(self):
        reg_user = AuthUserFactory()  # NOTE: AuthUserFactory sets password as 'queenfan86'
        url = self.user.get_claim_url(self.project._primary_key)
        # Follow to password re-enter page
        res = self.app.get(url, auth=reg_user.auth).follow(auth=reg_user.auth)

        # verify that the "Claim Account" form is returned
        assert_in('Claim Contributor', res.body)

        form = res.forms['claimContributorForm']
        form['password'] = 'queenfan86'
        res = form.submit(auth=reg_user.auth)
        res = res.follow(auth=reg_user.auth)

        self.project.reload()
        self.user.reload()
        # user is now a contributor to the project
        assert_in(reg_user, self.project.contributors)

        # the unregistered user (self.user) is removed as a contributor, and their
        assert_not_in(self.user, self.project.contributors)

        # unclaimed record for the project has been deleted
        assert_not_in(self.project, self.user.unclaimed_records)

    def test_claim_user_registered_preprint_with_correct_password(self):
        preprint = PreprintFactory(creator=self.referrer)
        name, email = fake.name(), fake_email()
        unreg_user = preprint.add_unregistered_contributor(
            fullname=name,
            email=email,
            auth=Auth(user=self.referrer)
        )
        reg_user = AuthUserFactory()  # NOTE: AuthUserFactory sets password as 'queenfan86'
        url = unreg_user.get_claim_url(preprint._id)
        # Follow to password re-enter page
        res = self.app.get(url, auth=reg_user.auth).follow(auth=reg_user.auth)

        # verify that the "Claim Account" form is returned
        assert_in('Claim Contributor', res.body)

        form = res.forms['claimContributorForm']
        form['password'] = 'queenfan86'
        res = form.submit(auth=reg_user.auth)

        preprint.reload()
        unreg_user.reload()
        # user is now a contributor to the project
        assert_in(reg_user, preprint.contributors)

        # the unregistered user (unreg_user) is removed as a contributor, and their
        assert_not_in(unreg_user, preprint.contributors)

        # unclaimed record for the project has been deleted
        assert_not_in(preprint, unreg_user.unclaimed_records)


class TestResendConfirmation(OsfTestCase):

    def setUp(self):
        super(TestResendConfirmation, self).setUp()
        self.unconfirmed_user = UnconfirmedUserFactory()
        self.confirmed_user = UserFactory()
        self.get_url = web_url_for('resend_confirmation_get')
        self.post_url = web_url_for('resend_confirmation_post')

    # test that resend confirmation page is load correctly
    def test_resend_confirmation_get(self):
        res = self.app.get(self.get_url)
        assert_equal(res.status_code, 200)
        assert_in('Resend Confirmation', res.body)
        assert_in('resendForm', res.forms)

    # test that unconfirmed user can receive resend confirmation email
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_can_receive_resend_confirmation_email(self, mock_send_mail):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['resendForm']
        form['email'] = self.unconfirmed_user.unconfirmed_emails[0]
        res = form.submit()

        # check email, request and response
        assert_true(mock_send_mail.called)
        assert_equal(res.status_code, 200)
        assert_equal(res.request.path, self.post_url)
        assert_in_html('If there is an OSF account', res)

    # test that confirmed user cannot receive resend confirmation email
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_cannot_receive_resend_confirmation_email_1(self, mock_send_mail):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['resendForm']
        form['email'] = self.confirmed_user.emails.first().address
        res = form.submit()

        # check email, request and response
        assert_false(mock_send_mail.called)
        assert_equal(res.status_code, 200)
        assert_equal(res.request.path, self.post_url)
        assert_in_html('has already been confirmed', res)

    # test that non-existing user cannot receive resend confirmation email
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_cannot_receive_resend_confirmation_email_2(self, mock_send_mail):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['resendForm']
        form['email'] = 'random@random.com'
        res = form.submit()

        # check email, request and response
        assert_false(mock_send_mail.called)
        assert_equal(res.status_code, 200)
        assert_equal(res.request.path, self.post_url)
        assert_in_html('If there is an OSF account', res)

    # test that user cannot submit resend confirmation request too quickly
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_cannot_resend_confirmation_twice_quickly(self, mock_send_mail):
        # load resend confirmation page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['resendForm']
        form['email'] = self.unconfirmed_user.email
        res = form.submit()
        res = form.submit()

        # check request and response
        assert_equal(res.status_code, 200)
        assert_in_html('Please wait', res)


class TestForgotPassword(OsfTestCase):

    def setUp(self):
        super(TestForgotPassword, self).setUp()
        self.user = UserFactory()
        self.auth_user = AuthUserFactory()
        self.get_url = web_url_for('forgot_password_get')
        self.post_url = web_url_for('forgot_password_post')
        self.user.verification_key_v2 = {}
        self.user.save()

    # log users out before they land on forgot password page
    def test_forgot_password_logs_out_user(self):
        # visit forgot password link while another user is logged in
        res = self.app.get(self.get_url, auth=self.auth_user.auth)
        # check redirection to CAS logout
        assert_equal(res.status_code, 302)
        location = res.headers.get('Location')
        assert_not_in('reauth', location)
        assert_in('logout?service=', location)
        assert_in('forgotpassword', location)

    # test that forgot password page is loaded correctly
    def test_get_forgot_password(self):
        res = self.app.get(self.get_url)
        assert_equal(res.status_code, 200)
        assert_in('Forgot Password', res.body)
        assert_in('forgotPasswordForm', res.forms)

    # test that existing user can receive reset password email
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_can_receive_reset_password_email(self, mock_send_mail):
        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['forgotPasswordForm']
        form['forgot_password-email'] = self.user.username
        res = form.submit()

        # check mail was sent
        assert_true(mock_send_mail.called)
        # check http 200 response
        assert_equal(res.status_code, 200)
        # check request URL is /forgotpassword
        assert_equal(res.request.path, self.post_url)
        # check push notification
        assert_in_html('If there is an OSF account', res)
        assert_not_in_html('Please wait', res)

        # check verification_key_v2 is set
        self.user.reload()
        assert_not_equal(self.user.verification_key_v2, {})

    # test that non-existing user cannot receive reset password email
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_cannot_receive_reset_password_email(self, mock_send_mail):
        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['forgotPasswordForm']
        form['forgot_password-email'] = 'fake' + self.user.username
        res = form.submit()

        # check mail was not sent
        assert_false(mock_send_mail.called)
        # check http 200 response
        assert_equal(res.status_code, 200)
        # check request URL is /forgotpassword
        assert_equal(res.request.path, self.post_url)
        # check push notification
        assert_in_html('If there is an OSF account', res)
        assert_not_in_html('Please wait', res)

        # check verification_key_v2 is not set
        self.user.reload()
        assert_equal(self.user.verification_key_v2, {})

    # test that non-existing user cannot receive reset password email
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_not_active_user_no_reset_password_email(self, mock_send_mail):
        self.user.disable_account()
        self.user.save()

        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['forgotPasswordForm']
        form['forgot_password-email'] = self.user.username
        res = form.submit()

        # check mail was not sent
        assert_false(mock_send_mail.called)
        # check http 200 response
        assert_equal(res.status_code, 200)
        # check request URL is /forgotpassword
        assert_equal(res.request.path, self.post_url)
        # check push notification
        assert_in_html('If there is an OSF account', res)
        assert_not_in_html('Please wait', res)

        # check verification_key_v2 is not set
        self.user.reload()
        assert_equal(self.user.verification_key_v2, {})

    # test that user cannot submit forgot password request too quickly
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_cannot_reset_password_twice_quickly(self, mock_send_mail):
        # load forgot password page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['forgotPasswordForm']
        form['forgot_password-email'] = self.user.username
        res = form.submit()
        res = form.submit()

        # check http 200 response
        assert_equal(res.status_code, 200)
        # check push notification
        assert_in_html('Please wait', res)
        assert_not_in_html('If there is an OSF account', res)


@unittest.skip('Public projects/components are dynamically loaded now.')
class TestAUserProfile(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)

        self.user = AuthUserFactory()
        self.me = AuthUserFactory()
        self.project = ProjectFactory(creator=self.me, is_public=True, title=fake.bs())
        self.component = NodeFactory(creator=self.me, parent=self.project, is_public=True, title=fake.bs())

    # regression test for https://github.com/CenterForOpenScience/osf.io/issues/2623
    def test_has_public_projects_and_components(self):
        # I go to my own profile
        url = web_url_for('profile_view_id', uid=self.me._primary_key)
        # I see the title of both my project and component
        res = self.app.get(url, auth=self.me.auth)
        assert_in_html(self.component.title, res)
        assert_in_html(self.project.title, res)

        # Another user can also see my public project and component
        url = web_url_for('profile_view_id', uid=self.me._primary_key)
        # I see the title of both my project and component
        res = self.app.get(url, auth=self.user.auth)
        assert_in_html(self.component.title, res)
        assert_in_html(self.project.title, res)

    def test_shows_projects_with_many_contributors(self):
        # My project has many contributors
        for _ in range(5):
            user = UserFactory()
            self.project.add_contributor(user, auth=Auth(self.project.creator), save=True)

        # I go to my own profile
        url = web_url_for('profile_view_id', uid=self.me._primary_key)
        res = self.app.get(url, auth=self.me.auth)
        # I see '3 more' as a link
        assert_in('3 more', res)

        res = res.click('3 more')
        assert_equal(res.request.path, self.project.url)

    def test_has_no_public_projects_or_components_on_own_profile(self):
        # User goes to their profile
        url = web_url_for('profile_view_id', uid=self.user._id)
        res = self.app.get(url, auth=self.user.auth)

        # user has no public components/projects
        assert_in('You have no public projects', res)
        assert_in('You have no public components', res)

    def test_user_no_public_projects_or_components(self):
        # I go to other user's profile
        url = web_url_for('profile_view_id', uid=self.user._id)
        # User has no public components/projects
        res = self.app.get(url, auth=self.me.auth)
        assert_in('This user has no public projects', res)
        assert_in('This user has no public components', res)

    # regression test
    def test_does_not_show_registrations(self):
        project = ProjectFactory(creator=self.user)
        component = NodeFactory(parent=project, creator=self.user, is_public=False)
        # User has a registration with public components
        reg = RegistrationFactory(project=component.parent_node, creator=self.user, is_public=True)
        for each in reg.nodes:
            each.is_public = True
            each.save()
        # I go to other user's profile
        url = web_url_for('profile_view_id', uid=self.user._id)
        # Registration does not appear on profile
        res = self.app.get(url, auth=self.me.auth)
        assert_in('This user has no public components', res)
        assert_not_in(reg.title, res)
        assert_not_in(reg.nodes[0].title, res)


@pytest.mark.enable_bookmark_creation
class TestPreprintBannerView(OsfTestCase):
    def setUp(self):
        super(TestPreprintBannerView, self).setUp()

        self.admin = AuthUserFactory()
        self.write_contrib = AuthUserFactory()
        self.read_contrib = AuthUserFactory()
        self.non_contrib = AuthUserFactory()
        self.provider_one = PreprintProviderFactory()
        self.project_one = ProjectFactory(creator=self.admin, is_public=True)
        self.project_one.add_contributor(self.write_contrib, permissions.WRITE)
        self.project_one.add_contributor(self.read_contrib, permissions.READ)

        self.subject_one = SubjectFactory()
        self.preprint = PreprintFactory(creator=self.admin, filename='mgla.pdf', provider=self.provider_one, subjects=[[self.subject_one._id]], project=self.project_one, is_published=True)
        self.preprint.add_contributor(self.write_contrib, permissions.WRITE)
        self.preprint.add_contributor(self.read_contrib, permissions.READ)

    def test_public_project_published_preprint(self):
        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_in('Has supplemental materials for', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_in('Has supplemental materials for', res.body)

    def test_public_project_abandoned_preprint(self):
        self.preprint.machine_state = 'initial'
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_not_in('Has supplemental materials for', res.body)

    def test_public_project_deleted_preprint(self):
        self.preprint.deleted = timezone.now()
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_not_in('Has supplemental materials for', res.body)

    def test_public_project_private_preprint(self):
        self.preprint.is_public = False
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_in('Has supplemental materials for', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_not_in('Has supplemental materials for', res.body)

    def test_public_project_orphaned_preprint(self):
        self.preprint.primary_file = None
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_in('Has supplemental materials for', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_not_in('Has supplemental materials for', res.body)

    def test_public_project_unpublished_preprint(self):
        self.preprint.is_published = False
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_in('Has supplemental materials for', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_in('Has supplemental materials for', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_not_in('Has supplemental materials for', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_not_in('Has supplemental materials for', res.body)

    def test_public_project_pending_preprint_post_moderation(self):
        self.preprint.machine_state = 'pending'
        provider = PreprintProviderFactory(reviews_workflow='post-moderation')
        self.preprint.provider = provider
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_in('Pending\n', res.body)
        assert_in('This preprint is publicly available and searchable but is subject to removal by a moderator.', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_in('Pending\n', res.body)
        assert_in('This preprint is publicly available and searchable but is subject to removal by a moderator.', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_in('Pending\n', res.body)
        assert_in('This preprint is publicly available and searchable but is subject to removal by a moderator.', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_in('on {}'.format(self.preprint.provider.name), res.body)
        assert_not_in('Pending\n', res.body)
        assert_not_in('This preprint is publicly available and searchable but is subject to removal by a moderator.', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_in('on {}'.format(self.preprint.provider.name), res.body)
        assert_not_in('Pending\n', res.body)
        assert_not_in('This preprint is publicly available and searchable but is subject to removal by a moderator.', res.body)

    def test_implicit_admins_can_see_project_status(self):
        project = ProjectFactory(creator=self.admin)
        component = NodeFactory(creator=self.admin, parent=project)
        project.add_contributor(self.write_contrib, permissions.ADMIN)
        project.save()

        preprint = PreprintFactory(creator=self.admin, filename='mgla.pdf', provider=self.provider_one, subjects=[[self.subject_one._id]], project=component, is_published=True)
        preprint.machine_state = 'pending'
        provider = PreprintProviderFactory(reviews_workflow='post-moderation')
        preprint.provider = provider
        preprint.save()
        url = component.web_url_for('view_project')

        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_in('{}'.format(preprint.provider.name), res.body)
        assert_in('Pending\n', res.body)
        assert_in('This preprint is publicly available and searchable but is subject to removal by a moderator.', res.body)

    def test_public_project_pending_preprint_pre_moderation(self):
        self.preprint.machine_state = 'pending'
        provider = PreprintProviderFactory(reviews_workflow='pre-moderation')
        self.preprint.provider = provider
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_in('Pending\n', res.body)
        assert_in('This preprint is not publicly available or searchable until approved by a moderator.', res.body)

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_in('Pending\n', res.body)
        assert_in('This preprint is not publicly available or searchable until approved by a moderator.', res.body)

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_in('Pending\n', res.body)
        assert_in('This preprint is not publicly available or searchable until approved by a moderator.', res.body)

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_not_in('Pending\n', res.body)
        assert_not_in('This preprint is not publicly available or searchable until approved by a moderator.', res.body)

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert_in('{}'.format(self.preprint.provider.name), res.body)
        assert_not_in('Pending\n', res.body)
        assert_not_in('This preprint is not publicly available or searchable until approved by a moderator.', res.body)

if __name__ == '__main__':
    unittest.main()
