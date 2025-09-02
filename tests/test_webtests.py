#!/usr/bin/env python3
"""Functional tests using WebTest."""
import logging
import unittest

import markupsafe
from unittest import mock
import pytest
import re
from bs4 import BeautifulSoup
from django.utils import timezone
from addons.wiki.utils import to_mongo_key
from framework.auth.core import Auth
from tests.base import OsfTestCase
from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PrivateLinkFactory,
    ProjectFactory,
    SubjectFactory,
    UserFactory,
)
from osf.utils import permissions
from addons.wiki.models import WikiPage, WikiVersion
from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from tests.utils import capture_notifications
from website.util import web_url_for

logging.getLogger('website.project.model').setLevel(logging.ERROR)


def assert_in_html(member, container):
    """Looks for the specified member in markupsafe-escaped HTML output"""
    member = markupsafe.escape(member)
    assert member in container


def assert_not_in_html(member, container):
    """Looks for the specified member in markupsafe-escaped HTML output"""
    member = markupsafe.escape(member)
    assert member not in container


class TestDisabledUser(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory()
        with capture_notifications():
            self.user.set_password('Korben Dallas')
        self.user.is_disabled = True
        self.user.save()

    def test_profile_disabled_returns_401(self):
        res = self.app.get(self.user.url)
        assert res.status_code == 410


class TestAnUnregisteredUser(OsfTestCase):

    def test_cant_see_profile_if_not_logged_in(self):
        url = web_url_for('profile_view')
        res = self.app.resolve_redirect(self.app.get(url))
        assert res.status_code == 308
        assert '/login/' in res.headers['Location']


@pytest.mark.enable_bookmark_creation
class TestAUser(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    def test_can_see_profile_url(self):
        res = self.app.get(self.user.url, follow_redirects=True)
        assert self.user.url in res.text

    # `GET /login/` without parameters is redirected to `/dashboard/` page which has `@must_be_logged_in` decorator
    # if user is not logged in, she/he is further redirected to CAS login page
    def test_is_redirected_to_cas_if_not_logged_in_at_login_page(self):
        res = self.app.resolve_redirect(self.app.get('/login/'))
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'login?service=' in location

    def test_is_redirected_to_dashboard_if_already_logged_in_at_login_page(self):
        res = self.app.get('/login/', auth=self.user.auth)
        assert res.status_code == 302
        assert 'dashboard' in res.headers.get('Location')

    def test_register_page(self):
        res = self.app.get('/register/')
        assert res.status_code == 200

    def test_is_redirected_to_dashboard_if_already_logged_in_at_register_page(self):
        res = self.app.get('/register/', auth=self.user.auth)
        assert res.status_code == 302
        assert 'dashboard' in res.headers.get('Location')

    def test_sees_projects_in_her_dashboard(self):
        # the user already has a project
        project = ProjectFactory(creator=self.user)
        project.add_contributor(self.user)
        project.save()
        res = self.app.get('/myprojects/', auth=self.user.auth)
        assert 'Projects' in res.text  # Projects heading

    def test_does_not_see_osffiles_in_user_addon_settings(self):
        res = self.app.get('/settings/addons/', auth=self.auth, follow_redirects=True)
        assert 'OSF Storage' not in res.text

    def test_sees_osffiles_in_project_addon_settings(self):
        project = ProjectFactory(creator=self.user)
        project.add_contributor(
            self.user,
            permissions=permissions.ADMIN,
            save=True)
        res = self.app.get(f'/{project._primary_key}/addons/', auth=self.auth, follow_redirects=True)
        assert 'OSF Storage' in res.text

    def test_sees_correct_title_on_dashboard(self):
        # User goes to dashboard
        res = self.app.get('/myprojects/', auth=self.auth, follow_redirects=True)
        title = res.html.title.string
        assert 'OSF | My Projects' == title

    def test_can_see_make_public_button_if_admin(self):
        # User is a contributor on a project
        project = ProjectFactory()
        project.add_contributor(
            self.user,
            permissions=permissions.ADMIN,
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth, follow_redirects=True)
        assert 'Make Public' in res.text

    def test_cant_see_make_public_button_if_not_admin(self):
        # User is a contributor on a project
        project = ProjectFactory()
        project.add_contributor(
            self.user,
            permissions=permissions.WRITE,
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth, follow_redirects=True)
        assert 'Make Public' not in res.text

    def test_can_see_make_private_button_if_admin(self):
        # User is a contributor on a project
        project = ProjectFactory(is_public=True)
        project.add_contributor(
            self.user,
            permissions=permissions.ADMIN,
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth, follow_redirects=True)
        assert 'Make Private' in res.text

    def test_cant_see_make_private_button_if_not_admin(self):
        # User is a contributor on a project
        project = ProjectFactory(is_public=True)
        project.add_contributor(
            self.user,
            permissions=permissions.WRITE,
            save=True)
        # User goes to the project page
        res = self.app.get(project.url, auth=self.auth, follow_redirects=True)
        assert 'Make Private' not in res.text

    def test_sees_logs_on_a_project(self):
        project = ProjectFactory(is_public=True)
        # User goes to the project's page
        res = self.app.get(project.url, auth=self.auth, follow_redirects=True)
        # Can see log event
        assert 'created' in res.text

    def test_no_wiki_content_message(self):
        project = ProjectFactory(creator=self.user)
        # Goes to project's wiki, where there is no content
        res = self.app.get(f'/{project._primary_key}/wiki/home/', auth=self.auth)
        # Sees a message indicating no content
        assert 'Add important information, links, or images here to describe your project.' in res.text
        # Sees that edit panel is open by default when home wiki has no content
        assert 'panelsUsed: ["view", "menu", "edit"]' in res.text

    def test_wiki_content(self):
        project = ProjectFactory(creator=self.user)
        wiki_page_name = 'home'
        wiki_content = 'Kittens'
        wiki_page = WikiFactory(
            user=self.user,
            node=project,
        )
        WikiVersionFactory(
            wiki_page=wiki_page,
            content=wiki_content
        )
        res = self.app.get(f'/{project._primary_key}/wiki/{wiki_page_name}/', auth=self.auth)
        assert 'Add important information, links, or images here to describe your project.' not in res.text
        assert wiki_content in res.text
        assert 'panelsUsed: ["view", "menu"]' in res.text

    def test_wiki_page_name_non_ascii(self):
        project = ProjectFactory(creator=self.user)
        non_ascii = to_mongo_key('WöRlÐé')
        WikiPage.objects.create_for_node(project, 'WöRlÐé', 'new content', Auth(self.user))
        wv = WikiVersion.objects.get_for_node(project, non_ascii)
        assert wv.wiki_page.page_name.upper() == non_ascii.upper()

    def test_noncontributor_cannot_see_wiki_if_no_content(self):
        user2 = UserFactory()
        # user2 creates a public project and adds no wiki content
        project = ProjectFactory(creator=user2, is_public=True)
        # self navigates to project
        res = self.app.get(project.url, follow_redirects=True)
        # Should not see wiki widget (since non-contributor and no content)
        assert 'Add important information, links, or images here to describe your project.' not in res.text

    def test_wiki_does_not_exist(self):
        project = ProjectFactory(creator=self.user)
        res = self.app.get(f'/{project._primary_key}/wiki/not a real page yet/', auth=self.auth)
        assert 'Add important information, links, or images here to describe your project.' in res.text

    def test_sees_own_profile(self):
        res = self.app.get('/profile/', auth=self.auth)
        td1 = res.html.find('td', text=re.compile(r'Public(.*?)Profile'))
        td2 = td1.find_next_sibling('td')
        assert td2.text == self.user.display_absolute_url

    def test_sees_another_profile(self):
        user2 = UserFactory()
        res = self.app.get(user2.url, auth=self.auth)
        td1 = res.html.find('td', text=re.compile(r'Public(.*?)Profile'))
        td2 = td1.find_next_sibling('td')
        assert td2.text == user2.display_absolute_url


@pytest.mark.enable_bookmark_creation
class TestComponents(OsfTestCase):

    def setUp(self):
        super().setUp()
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
        res = self.app.get(self.component.url, auth=self.user.auth, follow_redirects=True)
        parent_title = BeautifulSoup(res.text).find_all('h2', class_='node-parent-title')
        assert len(parent_title) == 1
        assert self.project.title in parent_title[0].text  # Bs4 will handle unescaping HTML here

    def test_delete_project(self):
        res = self.app.get(
            self.component.url + 'settings/',
            auth=self.user.auth,
            follow_redirects=True
        )
        assert f'Delete {self.component.project_or_component}' in res.text

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
            auth=non_admin.auth,
            follow_redirects=True
        )
        assert f'Delete {self.component.project_or_component}' not in res.text

    def test_can_configure_comments_if_admin(self):
        res = self.app.get(
            self.component.url + 'settings/',
            auth=self.user.auth,
            follow_redirects=True
        )
        assert 'Commenting' in res.text

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
            auth=non_admin.auth,
            follow_redirects=True
        )
        assert 'Commenting' not in res.text

    def test_components_should_have_component_list(self):
        res = self.app.get(self.component.url, auth=self.user.auth)
        assert 'Components' in res.text


@pytest.mark.enable_bookmark_creation
class TestPrivateLinkView(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()  # Is NOT a contributor
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory(anonymous=True)
        self.link.nodes.add(self.project)
        self.link.save()
        self.project_url = self.project.web_url_for('view_project')

    def test_anonymous_link_hide_contributor(self):
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key})
        assert 'Anonymous Contributors' in res.text
        assert self.user.fullname not in res.text

    def test_anonymous_link_hides_citations(self):
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key})
        assert 'Citation:' not in res.text

    def test_no_warning_for_read_only_user_with_valid_link(self):
        link2 = PrivateLinkFactory(anonymous=False)
        link2.nodes.add(self.project)
        link2.save()
        self.project.add_contributor(
            self.user,
            permissions=permissions.READ,
            save=True,
        )
        res = self.app.get(self.project_url, query_string={'view_only': link2.key},
                           auth=self.user.auth)
        assert ('is being viewed through a private, view-only link. '
                'Anyone with the link can view this project. '
                'Keep the link safe.') not in res.text

    def test_no_warning_for_read_only_user_with_invalid_link(self):
        self.project.add_contributor(
            self.user,
            permissions=permissions.READ,
            save=True,
        )
        res = self.app.get(self.project_url, query_string={'view_only': 'not_valid'},
                           auth=self.user.auth)
        assert ('is being viewed through a private, view-only link. '
                'Anyone with the link can view this project. '
                'Keep the link safe.') not in res.text

@pytest.mark.enable_bookmark_creation
class TestMergingAccounts(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = UserFactory.build()
        self.user.fullname = "tess' test string"
        with capture_notifications():
            self.user.set_password('science')
        self.user.save()
        self.dupe = UserFactory.build()
        with capture_notifications():
            self.dupe.set_password('example')
        self.dupe.save()

    def test_merged_user_is_not_shown_as_a_contributor(self):
        project = ProjectFactory(is_public=True)
        # Both the master and dupe are contributors
        project.add_contributor(self.dupe, log=False)
        project.add_contributor(self.user, log=False)
        project.save()
        # At the project page, both are listed as contributors
        res = self.app.get(project.url, follow_redirects=True)
        assert_in_html(self.user.fullname, res.text)
        assert_in_html(self.dupe.fullname, res.text)
        # The accounts are merged
        self.user.merge_user(self.dupe)
        self.user.save()
        # Now only the master user is shown at the project page
        res = self.app.get(project.url, follow_redirects=True)
        assert_in_html(self.user.fullname, res.text)
        assert self.dupe.is_merged
        assert self.dupe.fullname not in res.text

    def test_merged_user_has_alert_message_on_profile(self):
        # Master merges dupe
        self.user.merge_user(self.dupe)
        self.user.save()
        # At the dupe user's profile there is an alert message at the top
        # indicating that the user is merged
        res = self.app.get(f'/profile/{self.dupe._primary_key}/', follow_redirects=True)
        assert 'This account has been merged' in res.text


@pytest.mark.enable_bookmark_creation
class TestShortUrls(OsfTestCase):

    def setUp(self):
        super().setUp()
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
            auth=self.auth,
            follow_redirects=True
        ).text

    # In the following tests, we need to patch `framework.csrf.handlers.get_current_user_id`
    # because in `framework.csrf.handlers.after_request`, the call to `get_current_user_id`
    # will always return None when we make requests with basic auth. That means csrf_token
    # for every basic auth request will be different, which should be the correct behavior.
    # But it breaks the assertions because the server-side rendered forms in the body carries different
    # csrf tokens.
    # The original tests are written without the patch, and they pass because
    # `get_current_user_id` returned a truthy value even for basic auth requests
    # because of some hack that we did, resulting in same csrf token across different basic auth requests.

    def test_project_url(self):
        with mock.patch('framework.csrf.handlers.get_current_user_id', return_value=self.user._id):
            assert self._url_to_body(self.project.deep_url) == self._url_to_body(self.project.url)

    def test_component_url(self):
        with mock.patch('framework.csrf.handlers.get_current_user_id', return_value=self.user._id):
            assert self._url_to_body(self.component.deep_url) == self._url_to_body(self.component.url)

    def test_wiki_url(self):
        with mock.patch('framework.csrf.handlers.get_current_user_id', return_value=self.user._id):
            assert self._url_to_body(self.wiki.deep_url) == self._url_to_body(self.wiki.url)


@pytest.mark.enable_bookmark_creation
class TestPreprintBannerView(OsfTestCase):
    def setUp(self):
        super().setUp()

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
        assert 'Has supplemental materials for' in res.text

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert 'Has supplemental materials for' in res.text

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert 'Has supplemental materials for' in res.text

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert 'Has supplemental materials for' in res.text

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert 'Has supplemental materials for' in res.text

    def test_public_project_abandoned_preprint(self):
        self.preprint.machine_state = 'initial'
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert 'Has supplemental materials for' not in res.text

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert 'Has supplemental materials for' not in res.text

    def test_public_project_deleted_preprint(self):
        self.preprint.deleted = timezone.now()
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert 'Has supplemental materials for' not in res.text

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert 'Has supplemental materials for' not in res.text

    def test_public_project_private_preprint(self):
        self.preprint.is_public = False
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert 'Has supplemental materials for' in res.text

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert 'Has supplemental materials for' in res.text

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert 'Has supplemental materials for' in res.text

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert 'Has supplemental materials for' not in res.text

    def test_public_project_unpublished_preprint(self):
        self.preprint.is_published = False
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert 'Has supplemental materials for' in res.text

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert 'Has supplemental materials for' in res.text

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert 'Has supplemental materials for' in res.text

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert 'Has supplemental materials for' not in res.text

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert 'Has supplemental materials for' not in res.text

    def test_public_project_pending_preprint_post_moderation(self):
        self.preprint.machine_state = 'pending'
        provider = PreprintProviderFactory(reviews_workflow='post-moderation')
        self.preprint.provider = provider
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' in res.text
        print('res.text', res.text)
        assert 'This preprint is publicly available and searchable but is subject to removal by a moderator.' in res.text

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' in res.text
        assert 'This preprint is publicly available and searchable but is subject to removal by a moderator.' in res.text

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' in res.text
        assert 'This preprint is publicly available and searchable but is subject to removal by a moderator.' in res.text

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert f'on {self.preprint.provider.name}' in res.text
        assert 'Pending\n' not in res.text
        assert 'This preprint is publicly available and searchable but is subject to removal by a moderator.' not in res.text

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert f'on {self.preprint.provider.name}' in res.text
        assert 'Pending\n' not in res.text
        assert 'This preprint is publicly available and searchable but is subject to removal by a moderator.' not in res.text

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
        assert f'{preprint.provider.name}' in res.text
        assert 'Pending\n' in res.text
        assert 'This preprint is publicly available and searchable but is subject to removal by a moderator.' in res.text

    def test_public_project_pending_preprint_pre_moderation(self):
        self.preprint.machine_state = 'pending'
        provider = PreprintProviderFactory(reviews_workflow='pre-moderation')
        self.preprint.provider = provider
        self.preprint.save()

        url = self.project_one.web_url_for('view_project')

        # Admin - preprint
        res = self.app.get(url, auth=self.admin.auth)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' in res.text
        assert 'This preprint is not publicly available or searchable until approved by a moderator.' in res.text

        # Write - preprint
        res = self.app.get(url, auth=self.write_contrib.auth)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' in res.text
        assert 'This preprint is not publicly available or searchable until approved by a moderator.' in res.text

        # Read - preprint
        res = self.app.get(url, auth=self.read_contrib.auth)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' in res.text
        assert 'This preprint is not publicly available or searchable until approved by a moderator.'in res.text

        # Noncontrib - preprint
        res = self.app.get(url, auth=self.non_contrib.auth)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' not in res.text
        assert 'This preprint is not publicly available or searchable until approved by a moderator.' not in res.text

        # Unauthenticated - preprint
        res = self.app.get(url)
        assert f'{self.preprint.provider.name}' in res.text
        assert 'Pending\n' not in res.text
        assert 'This preprint is not publicly available or searchable until approved by a moderator.' not in res.text

if __name__ == '__main__':
    unittest.main()
