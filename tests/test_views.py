#!/usr/bin/env python3
"""Views tests for the OSF."""
from unittest.mock import MagicMock, ANY
from urllib import parse

import datetime as dt
import time
import unittest
from hashlib import md5
from http.cookies import SimpleCookie
from unittest import mock
from urllib.parse import quote_plus, unquote_plus

import pytest
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from flask import request, g
from lxml import html
from pytest import approx
from rest_framework import status as http_status
from werkzeug.test import ClientRedirectError

from addons.github.tests.factories import GitHubAccountFactory
from addons.osfstorage import settings as osfstorage_settings
from addons.wiki.models import WikiPage
from api_tests.utils import create_test_file
from framework import auth
from framework.auth import Auth, authenticate, cas, core
from framework.auth.campaigns import (
    get_campaigns,
    is_institution_login,
    is_native_login,
    is_proxy_login,
    campaign_url_for
)
from framework.auth.exceptions import InvalidTokenError
from framework.auth.utils import impute_names_model, ensure_external_identity_uniqueness
from framework.auth.views import login_and_register_handler
from framework.celery_tasks import handlers
from framework.exceptions import HTTPError, TemplateHTTPError
from framework.flask import redirect
from framework.transactions.handlers import no_auto_transaction
from osf.external.spam import tasks as spam_tasks
from osf.models import (
    Comment,
    AbstractNode,
    NodeLog,
    OSFUser,
    Tag,
    SpamStatus,
    NodeRelation,
    NotableDomain
)
from osf.utils import permissions
from osf_tests.factories import (
    fake_email,
    ApiOAuth2ApplicationFactory,
    ApiOAuth2PersonalTokenFactory,
    AuthUserFactory,
    CollectionFactory,
    CommentFactory,
    InstitutionFactory,
    NodeFactory,
    OSFGroupFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PrivateLinkFactory,
    ProjectFactory,
    ProjectWithAddonFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
    UserFactory,
    UnconfirmedUserFactory,
    UnregUserFactory,
    RegionFactory,
    DraftRegistrationFactory,
)
from tests.base import (
    assert_is_redirect,
    capture_signals,
    fake,
    get_default_metaschema,
    OsfTestCase,
    assert_datetime_equal,
    test_app
)
from tests.test_cas_authentication import generate_external_user_with_resp
from tests.utils import run_celery_tasks
from website import mailchimp_utils, mails, settings, language
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.profile.views import update_osf_help_mails_subscription
from website.project.decorators import check_can_access
from website.project.model import has_anonymous_link
from website.project.signals import contributor_added
from website.project.views.contributor import (
    deserialize_contributors,
    notify_added_contributor,
    send_claim_email,
    send_claim_registered_email,
)
from website.project.views.node import _should_show_wiki_widget, abbrev_authors
from website.settings import MAILCHIMP_GENERAL_LIST
from website.util import api_url_for, web_url_for
from website.util import rubeus
from website.util.metrics import OsfSourceTags, OsfClaimedTags, provider_source_tag, provider_claimed_tag

pytestmark = pytest.mark.django_db


@test_app.route('/errorexc')
def error_exc():
    UserFactory()
    raise RuntimeError

@test_app.route('/error500')
def error500():
    UserFactory()
    return 'error', 500

@test_app.route('/noautotransact')
@no_auto_transaction
def no_auto_transact():
    UserFactory()
    return 'error', 500

class TestViewsAreAtomic(OsfTestCase):
    def test_error_response_rolls_back_transaction(self):
        original_user_count = OSFUser.objects.count()
        self.app.get('/error500')
        assert OSFUser.objects.count() == original_user_count

        # Need to set debug = False in order to rollback transactions in transaction_teardown_request
        test_app.debug = False
        try:
            self.app.get('/errorexc')
        except RuntimeError:
            pass
        test_app.debug = True

        self.app.get('/noautotransact')
        assert OSFUser.objects.count() == original_user_count + 1


@pytest.mark.enable_bookmark_creation
class TestViewingProjectWithPrivateLink(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()  # Is NOT a contributor
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory()
        self.link.nodes.add(self.project)
        self.link.save()
        self.project_url = self.project.web_url_for('view_project')

    def test_edit_private_link_empty(self):
        node = ProjectFactory(creator=self.user)
        link = PrivateLinkFactory()
        link.nodes.add(node)
        link.save()
        url = node.api_url_for('project_private_link_edit')
        res = self.app.put(url, json={'pk': link._id, 'value': ''}, auth=self.user.auth)
        assert res.status_code == 400
        assert 'Title cannot be blank' in res.text

    def test_edit_private_link_invalid(self):
        node = ProjectFactory(creator=self.user)
        link = PrivateLinkFactory()
        link.nodes.add(node)
        link.save()
        url = node.api_url_for('project_private_link_edit')
        res = self.app.put(url, json={'pk': link._id, 'value': '<a></a>'}, auth=self.user.auth)
        assert res.status_code == 400
        assert 'Invalid link name.' in res.text

    @mock.patch('framework.auth.core.Auth.private_link')
    def test_can_be_anonymous_for_public_project(self, mock_property):
        mock_property.return_value(mock.MagicMock())
        mock_property.anonymous = True
        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.add(self.project)
        anonymous_link.save()
        self.project.set_privacy('public')
        self.project.save()
        self.project.reload()
        auth = Auth(user=self.user, private_key=anonymous_link.key)
        assert has_anonymous_link(self.project, auth)

    def test_has_private_link_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key})
        assert res.status_code == 200

    def test_not_logged_in_no_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': None})
        assert_is_redirect(res)
        res = self.app.resolve_redirect(res)
        assert res.status_code == 308
        assert res.request.path == '/login'

    def test_logged_in_no_private_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': None}, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_logged_in_has_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key}, auth=self.user.auth)
        assert res.status_code == 200

    @unittest.skip('Skipping for now until we find a way to mock/set the referrer')
    def test_prepare_private_key(self):
        res = self.app.get(self.project_url, query_string={'key': self.link.key})

        res = res.click('Registrations')

        assert_is_redirect(res)
        res = self.app.get(self.project_url, query_string={'key': self.link.key}, follow_redirects=True)

        assert res.status_code == 200
        assert res.request.GET['key'] == self.link.key

    def test_cannot_access_registrations_or_forks_with_anon_key(self):
        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.add(self.project)
        anonymous_link.save()
        self.project.is_public = False
        self.project.save()
        url = self.project_url + f'registrations/?view_only={anonymous_link.key}'
        res = self.app.get(url)

        assert res.status_code == 401

    def test_can_access_registrations_and_forks_with_not_anon_key(self):
        link = PrivateLinkFactory(anonymous=False)
        link.nodes.add(self.project)
        link.save()
        self.project.is_public = False
        self.project.save()
        url = self.project_url + f'registrations/?view_only={self.link.key}'
        res = self.app.get(url)

        assert res.status_code == 302
        assert url.replace('/project/', '') in res.location

    def test_check_can_access_valid(self):
        contributor = AuthUserFactory()
        self.project.add_contributor(contributor, auth=Auth(self.project.creator))
        self.project.save()
        assert check_can_access(self.project, contributor)

    def test_check_can_access_osf_group_member_valid(self):
        user = AuthUserFactory()
        group = OSFGroupFactory(creator=user)
        self.project.add_osf_group(group, permissions.READ)
        self.project.save()
        assert check_can_access(self.project, user)

    def test_check_user_access_invalid(self):
        noncontrib = AuthUserFactory()
        with pytest.raises(HTTPError):
            check_can_access(self.project, noncontrib)

    def test_check_user_access_if_user_is_None(self):
        assert not check_can_access(self.project, None)

    def test_check_can_access_invalid_access_requests_enabled(self):
        noncontrib = AuthUserFactory()
        assert self.project.access_requests_enabled
        with pytest.raises(TemplateHTTPError):
            check_can_access(self.project, noncontrib)

    def test_check_can_access_invalid_access_requests_disabled(self):
        noncontrib = AuthUserFactory()
        self.project.access_requests_enabled = False
        self.project.save()
        with pytest.raises(HTTPError):
            check_can_access(self.project, noncontrib)

    def test_logged_out_user_cannot_view_spammy_project_via_private_link(self):
        self.project.spam_status = SpamStatus.SPAM
        self.project.save()
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key})
        # Logged out user gets redirected to login page
        assert res.status_code == 302

    def test_logged_in_user_cannot_view_spammy_project_via_private_link(self):
        rando_user = AuthUserFactory()
        self.project.spam_status = SpamStatus.SPAM
        self.project.save()
        res = self.app.get(
            self.project_url,
            query_string={'view_only': self.link.key},
            auth=rando_user.auth,
        )
        assert res.status_code == 403


@pytest.mark.enable_bookmark_creation
class TestProjectViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user1 = AuthUserFactory()
        self.user1.save()
        self.consolidate_auth1 = Auth(user=self.user1)
        self.auth = self.user1.auth
        self.user2 = AuthUserFactory()
        self.auth2 = self.user2.auth
        # A project has 2 contributors
        self.project = ProjectFactory(
            title='Ham',
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()

        self.project2 = ProjectFactory(
            title='Tofu',
            description='Glazed',
            creator=self.user1
        )
        self.project2.add_contributor(self.user2, auth=Auth(self.user1))
        self.project2.save()

    @mock.patch('framework.status.push_status_message')
    def test_view_project_tos_status_message(self, mock_push_status_message):
        self.app.get(
            self.project.web_url_for('view_project'),
            auth=self.auth
        )
        assert mock_push_status_message.called
        assert 'terms_of_service' == mock_push_status_message.mock_calls[0][2]['id']

    @mock.patch('framework.status.push_status_message')
    def test_view_project_no_tos_status_message(self, mock_push_status_message):
        self.user1.accepted_terms_of_service = timezone.now()
        self.user1.save()
        self.app.get(
            self.project.web_url_for('view_project'),
            auth=self.auth
        )
        assert not mock_push_status_message.called

    def test_node_setting_with_multiple_matched_institution_email_domains(self):
        # User has alternate emails matching more than one institution's email domains
        inst1 = InstitutionFactory(email_domains=['foo.bar'])
        inst2 = InstitutionFactory(email_domains=['baz.qux'])

        user = AuthUserFactory()
        user.emails.create(address='queen@foo.bar')
        user.emails.create(address='brian@baz.qux')
        user.save()
        project = ProjectFactory(creator=user)

        # node settings page loads without error
        url = project.web_url_for('node_setting')
        res = self.app.get(url, auth=user.auth)
        assert res.status_code == 200

        # user is automatically affiliated with institutions
        # that matched email domains
        user.reload()
        assert inst1 in user.get_affiliated_institutions()
        assert inst2 in user.get_affiliated_institutions()

    def test_edit_title_empty(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('edit_node')
        res = self.app.post(url, json={'name': 'title', 'value': ''}, auth=self.user1.auth)
        assert res.status_code == 400
        assert 'Title cannot be blank' in res.text

    def test_edit_title_invalid(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('edit_node')
        res = self.app.post(url, json={'name': 'title', 'value': '<a></a>'}, auth=self.user1.auth)
        assert res.status_code == 400
        assert 'Invalid title.' in res.text

    def test_view_project_doesnt_select_for_update(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('view_project')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            res = self.app.get(url, auth=self.user1.auth)

        for_update_sql = connection.ops.for_update_sql()
        assert res.status_code == 200
        assert not any(for_update_sql in query['sql'] for query in ctx.captured_queries)

    def test_cannot_remove_only_visible_contributor(self):
        user1_contrib = self.project.contributor_set.get(user=self.user1)
        user1_contrib.visible = False
        user1_contrib.save()
        url = self.project.api_url_for('project_remove_contributor')
        res = self.app.post(
            url, json={'contributorID': self.user2._id,
                  'nodeIDs': [self.project._id]}, auth=self.auth
        )
        assert res.status_code == http_status.HTTP_403_FORBIDDEN
        assert res.json['message_long'] == 'Must have at least one bibliographic contributor'
        assert self.project.is_contributor(self.user2)

    def test_remove_only_visible_contributor_return_false(self):
        user1_contrib = self.project.contributor_set.get(user=self.user1)
        user1_contrib.visible = False
        user1_contrib.save()
        ret = self.project.remove_contributor(contributor=self.user2, auth=self.consolidate_auth1)
        assert not ret
        self.project.reload()
        assert self.project.is_contributor(self.user2)

    def test_can_view_nested_project_as_admin(self):
        self.parent_project = NodeFactory(
            title='parent project',
            category='project',
            parent=self.project,
            is_public=False
        )
        self.parent_project.save()
        self.child_project = NodeFactory(
            title='child project',
            category='project',
            parent=self.parent_project,
            is_public=False
        )
        self.child_project.save()
        url = self.child_project.web_url_for('view_project')
        res = self.app.get(url, auth=self.auth)
        assert 'Private Project' not in res.text
        assert 'parent project'in res.text

    def test_edit_description(self):
        url = f'/api/v1/project/{self.project._id}/edit/'
        self.app.post(url,
                           json={'name': 'description', 'value': 'Deep-fried'},
                           auth=self.auth)
        self.project.reload()
        assert self.project.description == 'Deep-fried'

    def test_project_api_url(self):
        url = self.project.api_url
        res = self.app.get(url, auth=self.auth)
        data = res.json
        assert data['node']['category'] == 'Project'
        assert data['node']['node_type'] == 'project'

        assert data['node']['title'] == self.project.title
        assert data['node']['is_public'] == self.project.is_public
        assert data['node']['is_registration'] == False
        assert data['node']['id'] == self.project._primary_key
        assert data['user']['is_contributor']
        assert data['node']['description'] == self.project.description
        assert data['node']['url'] == self.project.url
        assert data['node']['tags'] == list(self.project.tags.values_list('name', flat=True))
        assert 'forked_date' in data['node']
        assert 'registered_from_url' in data['node']
        # TODO: Test "parent" and "user" output

    def test_add_contributor_post(self):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        user2 = UserFactory()
        user3 = UserFactory()
        url = f'/api/v1/project/{project._id}/contributors/'

        dict2 = add_contributor_json(user2)
        dict3 = add_contributor_json(user3)
        dict2.update({
            'permission': permissions.ADMIN,
            'visible': True,
        })
        dict3.update({
            'permission': permissions.WRITE,
            'visible': False,
        })

        self.app.post(
            url,
            json={
                'users': [dict2, dict3],
                'node_ids': [project._id],
            },
            content_type='application/json',
            auth=self.auth,
            follow_redirects=True,
        )
        project.reload()
        assert user2 in project.contributors
        # A log event was added
        assert project.logs.latest().action == 'contributor_added'
        assert len(project.contributors) == 3

        assert project.has_permission(user2, permissions.ADMIN) is True
        assert project.has_permission(user2, permissions.WRITE) is True
        assert project.has_permission(user2, permissions.READ) is True

        assert project.has_permission(user3, permissions.ADMIN) is False
        assert project.has_permission(user3, permissions.WRITE) is True
        assert project.has_permission(user3, permissions.READ) is True

    def test_manage_permissions(self):
        url = self.project.api_url + 'contributors/manage/'
        self.app.post(
            url,
            json={
                'contributors': [
                    {'id': self.project.creator._id, 'permission': permissions.ADMIN,
                        'registered': True, 'visible': True},
                    {'id': self.user1._id, 'permission': permissions.READ,
                        'registered': True, 'visible': True},
                    {'id': self.user2._id, 'permission': permissions.ADMIN,
                        'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        self.project.reload()

        assert self.project.has_permission(self.user1, permissions.ADMIN) is False
        assert self.project.has_permission(self.user1, permissions.WRITE) is False
        assert self.project.has_permission(self.user1, permissions.READ) is True

        assert self.project.has_permission(self.user2, permissions.ADMIN) is True
        assert self.project.has_permission(self.user2, permissions.WRITE) is True
        assert self.project.has_permission(self.user2, permissions.READ) is True

    def test_manage_permissions_again(self):
        url = self.project.api_url + 'contributors/manage/'
        self.app.post(
            url,
            json={
                'contributors': [
                    {'id': self.user1._id, 'permission': permissions.ADMIN,
                     'registered': True, 'visible': True},
                    {'id': self.user2._id, 'permission': permissions.ADMIN,
                     'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        self.project.reload()
        self.app.post(
            url,
            json={
                'contributors': [
                    {'id': self.user1._id, 'permission': permissions.ADMIN,
                     'registered': True, 'visible': True},
                    {'id': self.user2._id, 'permission': permissions.READ,
                     'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        self.project.reload()

        assert self.project.has_permission(self.user2, permissions.ADMIN) is False
        assert self.project.has_permission(self.user2, permissions.WRITE) is False
        assert self.project.has_permission(self.user2, permissions.READ) is True

        assert self.project.has_permission(self.user1, permissions.ADMIN) is True
        assert self.project.has_permission(self.user1, permissions.WRITE) is True
        assert self.project.has_permission(self.user1, permissions.READ) is True

    def test_contributor_manage_reorder(self):

        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {'user': reg_user1, 'permissions': permissions.ADMIN, 'visible': True},
                {'user': reg_user2, 'permissions': permissions.ADMIN, 'visible': False},
            ]
        )
        # Add a non-registered user
        unregistered_user = project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=self.consolidate_auth1,
            save=True,
        )

        url = project.api_url + 'contributors/manage/'
        self.app.post(
            url,
            json={
                'contributors': [
                    {'id': reg_user2._id, 'permission': permissions.ADMIN,
                        'registered': True, 'visible': False},
                    {'id': project.creator._id, 'permission': permissions.ADMIN,
                        'registered': True, 'visible': True},
                    {'id': unregistered_user._id, 'permission': permissions.ADMIN,
                        'registered': False, 'visible': True},
                    {'id': reg_user1._id, 'permission': permissions.ADMIN,
                        'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        project.reload()

        # Note: Cast ForeignList to list for comparison
        assert list(project.contributors) == [reg_user2, project.creator, unregistered_user, reg_user1]

        assert list(project.visible_contributors) == [project.creator, unregistered_user, reg_user1]

    def test_project_remove_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.project._id]}
        self.app.post(url, json=payload,
                      auth=self.auth, follow_redirects=True)
        self.project.reload()
        assert self.user2._id not in self.project.contributors
        # A log event was added
        assert self.project.logs.latest().action == 'contributor_removed'

    def test_multiple_project_remove_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.project._id, self.project2._id]}
        res = self.app.post(url, json=payload,
                            auth=self.auth, follow_redirects=True)
        self.project.reload()
        self.project2.reload()
        assert self.user2._id not in self.project.contributors
        assert '/dashboard/' not in res.json

        assert self.user2._id not in self.project2.contributors
        # A log event was added
        assert self.project.logs.latest().action == 'contributor_removed'

    def test_private_project_remove_self_not_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # user2 removes self
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.project._id]}
        res = self.app.post(url, json=payload,
                            auth=self.auth2, follow_redirects=True)
        self.project.reload()
        assert res.status_code == 200
        assert res.json['redirectUrl'] == '/dashboard/'
        assert self.user2._id not in self.project.contributors

    def test_public_project_remove_self_not_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # user2 removes self
        self.public_project = ProjectFactory(creator=self.user1, is_public=True)
        self.public_project.add_contributor(self.user2, auth=Auth(self.user1))
        self.public_project.save()
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.public_project._id]}
        res = self.app.post(url, json=payload,
                            auth=self.auth2)
        self.public_project.reload()
        assert res.status_code == 200
        assert res.json['redirectUrl'] == '/' + self.public_project._id + '/'
        assert self.user2._id not in self.public_project.contributors

    def test_project_remove_other_not_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user1._id,
                   'nodeIDs': [self.project._id]}
        res = self.app.post(url, json=payload, auth=self.auth2)
        self.project.reload()
        assert res.status_code == 403
        expected_message = (
                'You do not have permission to perform this action. '
                'If this should not have occurred and the issue persists, '
                + language.SUPPORT_LINK
        )
        assert res.json['message_long'] == expected_message
        assert self.user1 in self.project.contributors

    def test_project_remove_fake_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': 'badid',
                   'nodeIDs': [self.project._id]}
        res = self.app.post(url, json=payload,
                            auth=self.auth, follow_redirects=True)
        self.project.reload()
        # Assert the contributor id was invalid
        assert res.status_code == 400
        assert res.json['message_long'] == 'Contributor not found.'
        assert 'badid' not in self.project.contributors

    def test_project_remove_self_only_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user1._id,
                   'nodeIDs': [self.project._id]}
        res = self.app.post(url, json=payload,
                            auth=self.auth, follow_redirects=True)

        self.project.reload()
        assert res.status_code == 400
        assert res.json['message_long'] == 'Could not remove contributor.'
        assert self.user1 in self.project.contributors

    def test_get_contributors_abbrev(self):
        # create a project with 3 registered contributors
        project = ProjectFactory(creator=self.user1, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {'user': reg_user1, 'permissions': permissions.ADMIN, 'visible': True},
                {'user': reg_user2, 'permissions': permissions.ADMIN, 'visible': True},
            ]
        )

        # add an unregistered contributor
        project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=self.consolidate_auth1,
            save=True,
        )

        url = project.api_url_for('get_node_contributors_abbrev')
        res = self.app.get(url, auth=self.auth)
        assert len(project.contributors) == 4
        assert len(res.json['contributors']) == 3
        assert len(res.json['others_count']) == 1
        assert res.json['contributors'][0]['separator'] == ','
        assert res.json['contributors'][1]['separator'] == ','
        assert res.json['contributors'][2]['separator'] == ' &'

    def test_edit_node_title(self):
        url = f'/api/v1/project/{self.project._id}/edit/'
        # The title is changed though posting form data
        self.app.post(url, json={'name': 'title', 'value': 'Bacon'},
                           auth=self.auth, follow_redirects=True)
        self.project.reload()
        # The title was changed
        assert self.project.title == 'Bacon'
        # A log event was saved
        assert self.project.logs.latest().action == 'edit_title'

    def test_add_tag(self):
        url = self.project.api_url_for('project_add_tag')
        self.app.post(url, json={'tag': "foo'ta#@%#%^&g?"}, auth=self.auth)
        self.project.reload()
        assert "foo'ta#@%#%^&g?" in self.project.tags.values_list('name', flat=True)
        assert "foo'ta#@%#%^&g?" == self.project.logs.latest().params['tag']

    def test_remove_tag(self):
        self.project.add_tag("foo'ta#@%#%^&g?", auth=self.consolidate_auth1, save=True)
        assert "foo'ta#@%#%^&g?" in self.project.tags.values_list('name', flat=True)
        url = self.project.api_url_for('project_remove_tag')
        self.app.delete(url, json={'tag': "foo'ta#@%#%^&g?"}, auth=self.auth)
        self.project.reload()
        assert "foo'ta#@%#%^&g?" not in self.project.tags.values_list('name', flat=True)
        latest_log = self.project.logs.latest()
        assert 'tag_removed' == latest_log.action
        assert "foo'ta#@%#%^&g?" == latest_log.params['tag']

    # Regression test for #OSF-5257
    def test_removal_empty_tag_throws_error(self):
        url = self.project.api_url_for('project_remove_tag')
        res = self.app.delete(url, json={'tag': ''}, auth=self.auth)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    # Regression test for #OSF-5257
    def test_removal_unknown_tag_throws_error(self):
        self.project.add_tag('narf', auth=self.consolidate_auth1, save=True)
        url = self.project.api_url_for('project_remove_tag')
        res = self.app.delete(url, json={'tag': 'troz'}, auth=self.auth)
        assert res.status_code == http_status.HTTP_409_CONFLICT

    def test_suspended_project(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        node.remove_node(Auth(self.user1))
        node.reload()
        node.suspended = True
        node.save()
        url = node.api_url
        res = self.app.get(url)
        assert res.status_code == 451

    def test_private_link_edit_name(self):
        link = PrivateLinkFactory(name='link')
        link.nodes.add(self.project)
        link.save()
        assert link.name == 'link'
        url = self.project.api_url + 'private_link/edit/'
        self.app.put(
            url,
            json={'pk': link._id, 'value': 'new name'},
            auth=self.auth, follow_redirects=True)
        self.project.reload()
        link.reload()
        assert link.name == 'new name'

    def test_remove_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete(
            url,
            json={'private_link_id': link._id},
            auth=self.auth,
            follow_redirects=True
        )
        self.project.reload()
        link.reload()
        assert link.is_deleted

    def test_remove_private_link_log(self):
        link = PrivateLinkFactory()
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete(
            url,
            json={'private_link_id': link._id},
            auth=self.auth,
            follow_redirects=True
        )

        last_log = self.project.logs.latest()
        assert last_log.action == NodeLog.VIEW_ONLY_LINK_REMOVED
        assert not last_log.params.get('anonymous_link')

    def test_remove_private_link_anonymous_log(self):
        link = PrivateLinkFactory(anonymous=True)
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete(
            url,
            json={'private_link_id': link._id},
            auth=self.auth,
            follow_redirects=True
        )

        last_log = self.project.logs.latest()
        assert last_log.action == NodeLog.VIEW_ONLY_LINK_REMOVED
        assert last_log.params.get('anonymous_link')

    def test_remove_component(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        url = node.api_url
        res = self.app.delete(url, json={}, auth=self.auth, follow_redirects=True)
        node.reload()
        assert node.is_deleted == True
        assert 'url' in res.json
        assert res.json['url'] == self.project.url

    def test_cant_remove_component_if_not_admin(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        non_admin = AuthUserFactory()
        node.add_contributor(
            non_admin,
            permissions=permissions.WRITE,
            save=True,
        )

        url = node.api_url
        res = self.app.delete(url, json={}, auth=non_admin.auth, follow_redirects=True)

        assert res.status_code == http_status.HTTP_403_FORBIDDEN
        assert not node.is_deleted

    def test_view_project_returns_whether_to_show_wiki_widget(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user, is_public=True)
        project.add_contributor(user)
        project.save()

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        assert 'show_wiki_widget' in res.json['user']

    def test_fork_grandcomponents_has_correct_root(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        child = NodeFactory(parent=project, creator=user)
        grand_child = NodeFactory(parent=child, creator=user)
        project.save()

        fork = project.fork_node(auth)
        fork.save()
        grand_child_fork = fork.nodes[0].nodes[0]
        assert grand_child_fork.root == fork

    def test_fork_count_does_not_include_deleted_forks(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        fork = project.fork_node(auth)
        project.save()
        fork.remove_node(auth)

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert 'fork_count' in res.json['node']
        assert 0 == res.json['node']['fork_count']

    def test_fork_count_does_not_include_fork_registrations(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        fork = project.fork_node(auth)
        project.save()
        registration = RegistrationFactory(project=fork)

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert 'fork_count'in res.json['node']
        assert 1 == res.json['node']['fork_count']

    def test_registration_retraction_redirect(self):
        url = self.project.web_url_for('node_registration_retraction_redirect')
        res = self.app.get(url, auth=self.auth)
        assert res.status_code == 302
        assert self.project.web_url_for('node_registration_retraction_get', _guid=True) in res.location

    def test_update_node(self):
        url = self.project.api_url_for('update_node')
        res = self.app.put(url, json={'title': 'newtitle'}, auth=self.auth)
        assert res.status_code == 200
        self.project.reload()
        assert self.project.title == 'newtitle'

    # Regression test
    def test_update_node_with_tags(self):
        self.project.add_tag('cheezebørger', auth=Auth(self.project.creator), save=True)
        url = self.project.api_url_for('update_node')
        res = self.app.put(url, json={'title': 'newtitle'}, auth=self.auth)
        assert res.status_code == 200
        self.project.reload()
        assert self.project.title == 'newtitle'

    # Regression test
    def test_retraction_view(self):
        project = ProjectFactory(creator=self.user1, is_public=True)

        registration = RegistrationFactory(project=project, is_public=True)
        reg_file = create_test_file(registration, user=registration.creator, create_guid=True)
        registration.retract_registration(self.user1)

        approval_token = registration.retraction.approval_state[self.user1._id]['approval_token']
        registration.retraction.approve_retraction(self.user1, approval_token)
        registration.save()

        url = registration.web_url_for('view_project')
        res = self.app.get(url, auth=self.auth)

        assert 'Mako Runtime Error' not in res.text
        assert registration.title in res.text
        assert res.status_code == 200

        for route in ['files', 'wiki/home', 'contributors', 'settings', 'withdraw', 'register', 'register/fakeid']:
            res = self.app.get(f'{url}{route}/', auth=self.auth)
            assert res.status_code == 302, route
            res = self.app.get(f'{url}{route}/', auth=self.auth, follow_redirects=True)
            assert res.status_code == 200, route
            assert 'This project is a withdrawn registration of' in res.text, route

        res = self.app.get(f'/{reg_file.guids.first()._id}/')
        assert res.status_code == 200
        assert 'This project is a withdrawn registration of' in res.text

class TestEditableChildrenViews(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.child = ProjectFactory(parent=self.project, creator=self.user, is_public=True)
        self.grandchild = ProjectFactory(parent=self.child, creator=self.user, is_public=False)
        self.great_grandchild = ProjectFactory(parent=self.grandchild, creator=self.user, is_public=True)
        self.great_great_grandchild = ProjectFactory(parent=self.great_grandchild, creator=self.user, is_public=False)
        url = self.project.api_url_for('get_editable_children')
        self.project_results = self.app.get(url, auth=self.user.auth).json

    def test_get_editable_children(self):
        assert len(self.project_results['children']) == 4
        assert self.project_results['node']['id'] == self.project._id

    def test_editable_children_order(self):
        assert self.project_results['children'][0]['id'] == self.child._id
        assert self.project_results['children'][1]['id'] == self.grandchild._id
        assert self.project_results['children'][2]['id'] == self.great_grandchild._id
        assert self.project_results['children'][3]['id'] == self.great_great_grandchild._id

    def test_editable_children_indents(self):
        assert self.project_results['children'][0]['indent'] == 0
        assert self.project_results['children'][1]['indent'] == 1
        assert self.project_results['children'][2]['indent'] == 2
        assert self.project_results['children'][3]['indent'] == 3

    def test_editable_children_parents(self):
        assert self.project_results['children'][0]['parent_id'] == self.project._id
        assert self.project_results['children'][1]['parent_id'] == self.child._id
        assert self.project_results['children'][2]['parent_id'] == self.grandchild._id
        assert self.project_results['children'][3]['parent_id'] == self.great_grandchild._id

    def test_editable_children_privacy(self):
        assert not self.project_results['node']['is_public']
        assert self.project_results['children'][0]['is_public']
        assert not self.project_results['children'][1]['is_public']
        assert self.project_results['children'][2]['is_public']
        assert not self.project_results['children'][3]['is_public']

    def test_editable_children_titles(self):
        assert self.project_results['node']['title'] == self.project.title
        assert self.project_results['children'][0]['title'] == self.child.title
        assert self.project_results['children'][1]['title'] == self.grandchild.title
        assert self.project_results['children'][2]['title'] == self.great_grandchild.title
        assert self.project_results['children'][3]['title'] == self.great_great_grandchild.title


class TestGetNodeTree(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()

    def test_get_single_node(self):
        project = ProjectFactory(creator=self.user)
        # child = NodeFactory(parent=project, creator=self.user)

        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)

        node_id = res.json[0]['node']['id']
        assert node_id == project._primary_key

    def test_get_node_with_children(self):
        project = ProjectFactory(creator=self.user)
        child1 = NodeFactory(parent=project, creator=self.user)
        child2 = NodeFactory(parent=project, creator=self.user2)
        child3 = NodeFactory(parent=project, creator=self.user)
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        child_ids = [child['node']['id'] for child in tree['children']]

        assert parent_node_id == project._primary_key
        assert child1._primary_key in child_ids
        assert child2._primary_key in child_ids
        assert child3._primary_key in child_ids

    def test_get_node_with_child_linked_to_parent(self):
        project = ProjectFactory(creator=self.user)
        child1 = NodeFactory(parent=project, creator=self.user)
        child1.save()
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        child1_id = tree['children'][0]['node']['id']
        assert child1_id == child1._primary_key

    def test_get_node_not_parent_owner(self):
        project = ProjectFactory(creator=self.user2)
        child = NodeFactory(parent=project, creator=self.user2)
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.json == []

    # Parent node should show because of user2 read access, and only child3
    def test_get_node_parent_not_admin(self):
        project = ProjectFactory(creator=self.user)
        project.add_contributor(self.user2, auth=Auth(self.user))
        project.save()
        child1 = NodeFactory(parent=project, creator=self.user)
        child2 = NodeFactory(parent=project, creator=self.user)
        child3 = NodeFactory(parent=project, creator=self.user)
        child3.add_contributor(self.user2, auth=Auth(self.user))
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user2.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        children = tree['children']
        assert parent_node_id == project._primary_key
        assert len(children) == 1
        assert children[0]['node']['id'] == child3._primary_key


@pytest.mark.enable_enqueue_task
@pytest.mark.enable_implicit_clean
class TestUserProfile(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()

    def test_unserialize_social(self):
        url = api_url_for('unserialize_social')
        payload = {
            'profileWebsites': ['http://frozen.pizza.com/reviews'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
        }
        with mock.patch.object(spam_tasks.requests, 'head'):
            resp = self.app.put(
                url,
                json=payload,
                auth=self.user.auth,
            )

        self.user.reload()
        for key, value in payload.items():
            assert self.user.social[key] == value
        assert self.user.social['researcherId'] is None

        assert NotableDomain.objects.all()
        assert NotableDomain.objects.get(domain='frozen.pizza.com')

    # Regression test for help-desk ticket
    def test_making_email_primary_is_not_case_sensitive(self):
        user = AuthUserFactory(username='fred@queen.test')
        # make confirmed email have different casing
        email = user.emails.first()
        email.address = email.address.capitalize()
        email.save()
        url = api_url_for('update_user')
        res = self.app.put(
            url,
            json={'id': user._id, 'emails': [{'address': 'fred@queen.test', 'primary': True, 'confirmed': True}]},
            auth=user.auth
        )
        assert res.status_code == 200

    def test_unserialize_social_validation_failure(self):
        url = api_url_for('unserialize_social')
        # profileWebsites URL is invalid
        payload = {
            'profileWebsites': ['http://goodurl.com', 'http://invalidurl'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
        }
        res = self.app.put(
            url,
            json=payload,
            auth=self.user.auth,

        )
        assert res.status_code == 400
        assert res.json['message_long'] == 'Invalid personal URL.'

    def test_serialize_social_editable(self):
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        with mock.patch.object(spam_tasks.requests, 'head'):
            self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert res.json.get('twitter') == 'howtopizza'
        assert res.json.get('profileWebsites') == ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        assert res.json.get('github') is None
        assert res.json['editable']

    def test_serialize_social_not_editable(self):
        user2 = AuthUserFactory()
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        with mock.patch.object(spam_tasks.requests, 'head'):
            self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        with mock.patch.object(spam_tasks.requests, 'head'):
            res = self.app.get(
                url,
                auth=user2.auth,
            )
        assert res.json.get('twitter') == 'howtopizza'
        assert res.json.get('profileWebsites') == ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        assert res.json.get('github') is None
        assert not res.json['editable']

    def test_serialize_social_addons_editable(self):
        self.user.add_addon('github')
        github_account = GitHubAccountFactory()
        github_account.save()
        self.user.external_accounts.add(github_account)
        self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert res.json['addons']['github'] == 'abc'

    def test_serialize_social_addons_not_editable(self):
        user2 = AuthUserFactory()
        self.user.add_addon('github')
        github_account = GitHubAccountFactory()
        github_account.save()
        self.user.external_accounts.add(github_account)
        self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        )
        assert 'addons' not in res.json

    def test_unserialize_and_serialize_jobs(self):
        jobs = [{
            'institution': 'an institution',
            'department': 'a department',
            'title': 'a title',
            'startMonth': 'January',
            'startYear': '2001',
            'endMonth': 'March',
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution': 'another institution',
            'department': None,
            'title': None,
            'startMonth': 'May',
            'startYear': '2001',
            'endMonth': None,
            'endYear': None,
            'ongoing': True,
        }]
        payload = {'contents': jobs}
        url = api_url_for('unserialize_jobs')
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert len(self.user.jobs) == 2
        url = api_url_for('serialize_jobs')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(jobs):
            assert job == res.json['contents'][i]

    def test_unserialize_and_serialize_schools(self):
        schools = [{
            'institution': 'an institution',
            'department': 'a department',
            'degree': 'a degree',
            'startMonth': 1,
            'startYear': '2001',
            'endMonth': 5,
            'endYear': '2001',
            'ongoing': False,
        }, {
            'institution': 'another institution',
            'department': None,
            'degree': None,
            'startMonth': 5,
            'startYear': '2001',
            'endMonth': None,
            'endYear': None,
            'ongoing': True,
        }]
        payload = {'contents': schools}
        url = api_url_for('unserialize_schools')
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert len(self.user.schools) == 2
        url = api_url_for('serialize_schools')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(schools):
            assert job == res.json['contents'][i]

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_jobs(self, mock_check_spam):
        jobs = [
            {
                'institution': fake.company(),
                'department': fake.catch_phrase(),
                'title': fake.bs(),
                'startMonth': 5,
                'startYear': '2013',
                'endMonth': 3,
                'endYear': '2014',
                'ongoing': False,
            }
        ]
        payload = {'contents': jobs}
        url = api_url_for('unserialize_jobs')
        res = self.app.put(url, json=payload, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        # jobs field is updated
        assert self.user.jobs == jobs
        assert mock_check_spam.called

    def test_unserialize_names(self):
        fake_fullname_w_spaces = f'    {fake.name()}    '
        names = {
            'full': fake_fullname_w_spaces,
            'given': 'Tea',
            'middle': 'Gray',
            'family': 'Pot',
            'suffix': 'Ms.',
        }
        url = api_url_for('unserialize_names')
        res = self.app.put(url, json=names, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        # user is updated
        assert self.user.fullname == fake_fullname_w_spaces.strip()
        assert self.user.given_name == names['given']
        assert self.user.middle_names == names['middle']
        assert self.user.family_name == names['family']
        assert self.user.suffix == names['suffix']

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_schools(self, mock_check_spam):
        schools = [
            {
                'institution': fake.company(),
                'department': fake.catch_phrase(),
                'degree': fake.bs(),
                'startMonth': 5,
                'startYear': '2013',
                'endMonth': 3,
                'endYear': '2014',
                'ongoing': False,
            }
        ]
        payload = {'contents': schools}
        url = api_url_for('unserialize_schools')
        res = self.app.put(url, json=payload, auth=self.user.auth)
        assert res.status_code == 200
        self.user.reload()
        # schools field is updated
        assert self.user.schools == schools
        assert mock_check_spam.called

    @mock.patch('osf.models.user.OSFUser.check_spam')
    def test_unserialize_jobs_valid(self, mock_check_spam):
        jobs = [
            {
                'institution': fake.company(),
                'department': fake.catch_phrase(),
                'title': fake.bs(),
                'startMonth': 5,
                'startYear': '2013',
                'endMonth': 3,
                'endYear': '2014',
                'ongoing': False,
            }
        ]
        payload = {'contents': jobs}
        url = api_url_for('unserialize_jobs')
        res = self.app.put(url, json=payload, auth=self.user.auth)
        assert res.status_code == 200
        assert mock_check_spam.called

    def test_update_user_timezone(self):
        assert self.user.timezone == 'Etc/UTC'
        payload = {'timezone': 'America/New_York', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.timezone == 'America/New_York'

    def test_update_user_locale(self):
        assert self.user.locale == 'en_US'
        payload = {'locale': 'de_DE', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.locale == 'de_DE'

    def test_update_user_locale_none(self):
        assert self.user.locale == 'en_US'
        payload = {'locale': None, 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.locale == 'en_US'

    def test_update_user_locale_empty_string(self):
        assert self.user.locale == 'en_US'
        payload = {'locale': '', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put(url, json=payload, auth=self.user.auth)
        self.user.reload()
        assert self.user.locale == 'en_US'

    def test_cannot_update_user_without_user_id(self):
        user1 = AuthUserFactory()
        url = api_url_for('update_user')
        header = {'emails': [{'address': user1.username}]}
        res = self.app.put(url, json=header, auth=user1.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == '"id" is required'

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_emails_return_emails(self, send_mail):
        user1 = AuthUserFactory()
        url = api_url_for('update_user')
        email = 'test@cos.io'
        header = {'id': user1._id,
                  'emails': [{'address': user1.username, 'primary': True, 'confirmed': True},
                             {'address': email, 'primary': False, 'confirmed': False}
                  ]}
        res = self.app.put(url, json=header, auth=user1.auth)
        assert res.status_code == 200
        assert 'emails' in res.json['profile']
        assert len(res.json['profile']['emails']) == 2

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_return_emails(self, send_mail):
        user1 = AuthUserFactory()
        url = api_url_for('resend_confirmation')
        email = 'test@cos.io'
        header = {'id': user1._id,
                  'email': {'address': email, 'primary': False, 'confirmed': False}
                  }
        res = self.app.put(url, json=header, auth=user1.auth)
        assert res.status_code == 200
        assert 'emails' in res.json['profile']
        assert len(res.json['profile']['emails']) == 2

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_update_user_mailing_lists(self, mock_get_mailchimp_api, send_mail):
        email = fake_email()
        email_hash = md5(email.lower().encode()).hexdigest()
        self.user.emails.create(address=email)
        list_name = MAILCHIMP_GENERAL_LIST
        self.user.mailchimp_mailing_lists[list_name] = True
        self.user.save()
        user_hash = md5(self.user.username.lower().encode()).hexdigest()

        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': 1, 'list_name': list_name}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)

        url = api_url_for('update_user', uid=self.user._id)
        emails = [
            {'address': self.user.username, 'primary': False, 'confirmed': True},
            {'address': email, 'primary': True, 'confirmed': True}]
        payload = {'locale': '', 'id': self.user._id, 'emails': emails}
        self.app.put(url, json=payload, auth=self.user.auth)
        # the test app doesn't have celery handlers attached, so we need to call this manually.
        handlers.celery_teardown_request()

        assert mock_client.lists.members.delete.called
        mock_client.lists.members.delete.assert_called_with(
            list_id=list_id,
            subscriber_hash=user_hash
        )
        mock_client.lists.members.create_or_update.assert_called_with(
            list_id=list_id,
            subscriber_hash=email_hash,
            data={
                'status': 'subscribed',
                'status_if_new': 'subscribed',
                'email_address': email,
                'merge_fields': {
                    'FNAME': self.user.given_name,
                    'LNAME': self.user.family_name
                }
            }
        )
        handlers.celery_teardown_request()

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_unsubscribe_mailchimp_not_called_if_user_not_subscribed(self, mock_get_mailchimp_api, send_mail):
        email = fake_email()
        self.user.emails.create(address=email)
        list_name = MAILCHIMP_GENERAL_LIST
        self.user.mailchimp_mailing_lists[list_name] = False
        self.user.save()

        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': 1, 'list_name': list_name}

        url = api_url_for('update_user', uid=self.user._id)
        emails = [
            {'address': self.user.username, 'primary': False, 'confirmed': True},
            {'address': email, 'primary': True, 'confirmed': True}]
        payload = {'locale': '', 'id': self.user._id, 'emails': emails}
        self.app.put(url, json=payload, auth=self.user.auth)

        assert mock_client.lists.members.delete.call_count == 0
        assert mock_client.lists.members.create_or_update.call_count == 0
        handlers.celery_teardown_request()

    def test_user_update_region(self):
        user_settings = self.user.get_addon('osfstorage')
        assert user_settings.default_region_id == 1

        url = '/api/v1/profile/region/'
        auth = self.user.auth
        region = RegionFactory(name='Frankfort', _id='eu-central-1')
        payload = {'region_id': 'eu-central-1'}

        res = self.app.put(url, json=payload, auth=auth)
        user_settings.reload()
        assert user_settings.default_region_id == region.id

    def test_user_update_region_missing_region_id_key(self):
        url = '/api/v1/profile/region/'
        auth = self.user.auth
        region = RegionFactory(name='Frankfort', _id='eu-central-1')
        payload = {'bad_key': 'eu-central-1'}

        res = self.app.put(url, json=payload, auth=auth)
        assert res.status_code == 400

    def test_user_update_region_missing_bad_region(self):
        url = '/api/v1/profile/region/'
        auth = self.user.auth
        payload = {'region_id': 'bad-region-1'}

        res = self.app.put(url, json=payload, auth=auth)
        assert res.status_code == 404

class TestUserProfileApplicationsPage(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.platform_app = ApiOAuth2ApplicationFactory(owner=self.user)
        self.detail_url = web_url_for('oauth_application_detail', client_id=self.platform_app.client_id)

    def test_non_owner_cant_access_detail_page(self):
        res = self.app.get(self.detail_url, auth=self.user2.auth)
        assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_owner_cant_access_deleted_application(self):
        self.platform_app.is_active = False
        self.platform_app.save()
        res = self.app.get(self.detail_url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_410_GONE

    def test_owner_cant_access_nonexistent_application(self):
        url = web_url_for('oauth_application_detail', client_id='nonexistent')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_404_NOT_FOUND

    def test_url_has_not_broken(self):
        assert self.platform_app.url == self.detail_url


class TestUserProfileTokensPage(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.token = ApiOAuth2PersonalTokenFactory()
        self.detail_url = web_url_for('personal_access_token_detail', _id=self.token._id)

    def test_url_has_not_broken(self):
        assert self.token.url == self.detail_url


class TestUserAccount(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.user.set_password('password')
        self.user.auth = (self.user.username, 'password')
        self.user.save()

    def test_password_change_valid(self,
                                   old_password='password',
                                   new_password='Pa$$w0rd',
                                   confirm_password='Pa$$w0rd'):
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': old_password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        res = self.app.post(url, data=post_data, auth=(self.user.username, old_password))
        assert res.status_code == 302
        res = self.app.post(url, data=post_data, auth=(self.user.username, new_password), follow_redirects=True)
        assert res.status_code == 200
        self.user.reload()
        assert self.user.check_password(new_password)

    @mock.patch('website.profile.views.push_status_message')
    def test_user_account_password_reset_query_params(self, mock_push_status_message):
        url = web_url_for('user_account') + '?password_reset=True'
        res = self.app.get(url, auth=self.user.auth)
        assert mock_push_status_message.called
        assert 'Password updated successfully' in mock_push_status_message.mock_calls[0][1][0]

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_invalid(self, mock_push_status_message, old_password='', new_password='',
                                     confirm_password='', error_message='Old password is invalid'):
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': old_password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert res.status_code == 302
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == 200
        self.user.reload()
        assert not self.user.check_password(new_password)
        assert mock_push_status_message.called
        error_strings = [e[1][0] for e in mock_push_status_message.mock_calls]
        assert error_message in error_strings

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_rate_limiting(self, mock_push_status_message):
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': 'invalid old password',
            'new_password': 'this is a new password',
            'confirm_password': 'this is a new password',
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 1
        assert res.status_code == 200
        # Make a second request
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert len( mock_push_status_message.mock_calls) == 2
        assert 'Old password is invalid' == mock_push_status_message.mock_calls[1][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 2

        # Make a third request
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert len(mock_push_status_message.mock_calls) == 3
        assert 'Old password is invalid' == mock_push_status_message.mock_calls[2][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 3

        # Make a fourth request
        res = self.app.post(url, data=post_data, auth=self.user.auth)
        assert mock_push_status_message.called
        error_strings = mock_push_status_message.mock_calls[3][2]
        assert 'Too many failed attempts' in error_strings['message']
        self.user.reload()
        # Too many failed requests within a short window.  Throttled.
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 3

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_rate_limiting_not_imposed_if_old_password_correct(self, mock_push_status_message):
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': 'password',
            'new_password': 'short',
            'confirm_password': 'short',
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        assert res.status_code == 200
        # Make a second request
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert len(mock_push_status_message.mock_calls) == 2
        assert 'Password should be at least eight characters' == mock_push_status_message.mock_calls[1][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0

        # Make a third request
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert len(mock_push_status_message.mock_calls) == 3
        assert 'Password should be at least eight characters' == mock_push_status_message.mock_calls[2][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0

        # Make a fourth request
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert mock_push_status_message.called
        assert len(mock_push_status_message.mock_calls) == 4
        assert 'Password should be at least eight characters' == mock_push_status_message.mock_calls[3][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0

    @mock.patch('website.profile.views.push_status_message')
    def test_old_password_invalid_attempts_reset_if_password_successfully_reset(self, mock_push_status_message):
        assert self.user.change_password_last_attempt is None
        assert self.user.old_password_invalid_attempts == 0
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': 'invalid old password',
            'new_password': 'this is a new password',
            'confirm_password': 'this is a new password',
        }
        correct_post_data = {
            'old_password': 'password',
            'new_password': 'thisisanewpassword',
            'confirm_password': 'thisisanewpassword',
        }
        res = self.app.post(url, data=post_data, auth=self.user.auth, follow_redirects=True)
        assert len(mock_push_status_message.mock_calls) == 1
        assert 'Old password is invalid' == mock_push_status_message.mock_calls[0][1][0]
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 1
        assert res.status_code == 200

        # Make a second request that successfully changes password
        res = self.app.post(url, data=correct_post_data, auth=self.user.auth)
        self.user.reload()
        assert self.user.change_password_last_attempt is not None
        assert self.user.old_password_invalid_attempts == 0

    def test_password_change_invalid_old_password(self):
        self.test_password_change_invalid(
            old_password='invalid old password',
            new_password='new password',
            confirm_password='new password',
            error_message='Old password is invalid',
        )

    def test_password_change_invalid_confirm_password(self):
        self.test_password_change_invalid(
            old_password='password',
            new_password='new password',
            confirm_password='invalid confirm password',
            error_message='Password does not match the confirmation',
        )

    def test_password_change_invalid_new_password_length(self):
        self.test_password_change_invalid(
            old_password='password',
            new_password='1234567',
            confirm_password='1234567',
            error_message='Password should be at least eight characters',
        )

    def test_password_change_valid_new_password_length(self):
        self.test_password_change_valid(
            old_password='password',
            new_password='12345678',
            confirm_password='12345678',
        )

    def test_password_change_invalid_blank_password(self, old_password='', new_password='', confirm_password=''):
        self.test_password_change_invalid(
            old_password=old_password,
            new_password=new_password,
            confirm_password=confirm_password,
            error_message='Passwords cannot be blank',
        )

    def test_password_change_invalid_empty_string_new_password(self):
        self.test_password_change_invalid_blank_password('password', '', 'new password')

    def test_password_change_invalid_blank_new_password(self):
        self.test_password_change_invalid_blank_password('password', '      ', 'new password')

    def test_password_change_invalid_empty_string_confirm_password(self):
        self.test_password_change_invalid_blank_password('password', 'new password', '')

    def test_password_change_invalid_blank_confirm_password(self):
        self.test_password_change_invalid_blank_password('password', 'new password', '      ')

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_user_cannot_request_account_export_before_throttle_expires(self, send_mail):
        url = api_url_for('request_export')
        self.app.post(url, auth=self.user.auth)
        assert send_mail.called
        res = self.app.post(url, auth=self.user.auth)
        assert res.status_code == 400
        assert send_mail.call_count == 1

    def test_get_unconfirmed_emails_exclude_external_identity(self):
        external_identity = {
            'service': {
                'AFI': 'LINK'
            }
        }
        self.user.add_unconfirmed_email('james@steward.com')
        self.user.add_unconfirmed_email('steward@james.com', external_identity=external_identity)
        self.user.save()
        unconfirmed_emails = self.user.get_unconfirmed_emails_exclude_external_identity()
        assert 'james@steward.com' in unconfirmed_emails
        assert 'steward@james.com'not in unconfirmed_emails


@pytest.mark.enable_implicit_clean
class TestAddingContributorViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator)
        self.auth = Auth(self.project.creator)
        # Authenticate all requests
        contributor_added.connect(notify_added_contributor)

    def test_serialize_unregistered_without_record(self):
        name, email = fake.name(), fake_email()
        res = serialize_unregistered(fullname=name, email=email)
        assert res['fullname'] == name
        assert res['email'] == email
        assert res['id'] is None
        assert not res['registered']
        assert res['profile_image_url']
        assert not res['active']

    def test_deserialize_contributors(self):
        contrib = UserFactory()
        unreg = UnregUserFactory()
        name, email = fake.name(), fake_email()
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [
            add_contributor_json(contrib),
            serialize_unregistered(fake.name(), unreg.username),
            unreg_no_record
        ]
        contrib_data[0]['permission'] = permissions.ADMIN
        contrib_data[1]['permission'] = permissions.WRITE
        contrib_data[2]['permission'] = permissions.READ
        contrib_data[0]['visible'] = True
        contrib_data[1]['visible'] = True
        contrib_data[2]['visible'] = True
        res = deserialize_contributors(
            self.project,
            contrib_data,
            auth=Auth(self.creator))
        assert len(res) == len(contrib_data)
        assert res[0]['user'].is_registered

        assert not res[1]['user'].is_registered
        assert res[1]['user']._id

        assert not res[2]['user'].is_registered
        assert res[2]['user']._id

    def test_deserialize_contributors_validates_fullname(self):
        name = '<img src=1 onerror=console.log(1)>'
        email = fake_email()
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [unreg_no_record]
        contrib_data[0]['permission'] = permissions.ADMIN
        contrib_data[0]['visible'] = True

        with pytest.raises(ValidationError):
            deserialize_contributors(
                self.project,
                contrib_data,
                auth=Auth(self.creator),
                validate=True)

    def test_deserialize_contributors_validates_email(self):
        name = fake.name()
        email = '!@#$%%^&*'
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [unreg_no_record]
        contrib_data[0]['permission'] = permissions.ADMIN
        contrib_data[0]['visible'] = True

        with pytest.raises(ValidationError):
            deserialize_contributors(
                self.project,
                contrib_data,
                auth=Auth(self.creator),
                validate=True)

    def test_serialize_unregistered_with_record(self):
        name, email = fake.name(), fake_email()
        user = self.project.add_unregistered_contributor(fullname=name,
                                                         email=email, auth=Auth(self.project.creator))
        self.project.save()
        res = serialize_unregistered(
            fullname=name,
            email=email
        )
        assert not res['active']
        assert not res['registered']
        assert res['id'] == user._primary_key
        assert res['profile_image_url']
        assert res['fullname'] == name
        assert res['email'] == email

    def test_add_contributor_with_unreg_contribs_and_reg_contribs(self):
        n_contributors_pre = len(self.project.contributors)
        reg_user = UserFactory()
        name, email = fake.name(), fake_email()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': email,
            'permission': permissions.ADMIN,
            'visible': True,
        }
        reg_dict = add_contributor_json(reg_user)
        reg_dict['permission'] = permissions.ADMIN
        reg_dict['visible'] = True
        payload = {
            'users': [reg_dict, pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        self.project.reload()
        assert len(self.project.contributors) == n_contributors_pre + len(payload['users'])

        new_unreg = auth.get_user(email=email)
        assert not new_unreg.is_registered
        # unclaimed record was added
        new_unreg.reload()
        assert self.project._primary_key in new_unreg.unclaimed_records
        rec = new_unreg.get_unclaimed_record(self.project._primary_key)
        assert rec['name'] == name
        assert rec['email'] == email

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_add_contributors_post_only_sends_one_email_to_unreg_user(
            self, mock_send_claim_email):
        # Project has components
        comp1, comp2 = NodeFactory(
            creator=self.creator), NodeFactory(creator=self.creator)
        NodeRelation.objects.create(parent=self.project, child=comp1)
        NodeRelation.objects.create(parent=self.project, child=comp2)
        self.project.save()

        # An unreg user is added to the project AND its components
        unreg_user = {  # dict because user has not previous unreg record
            'id': None,
            'registered': False,
            'fullname': fake.name(),
            'email': fake_email(),
            'permission': permissions.ADMIN,
            'visible': True,
        }
        payload = {
            'users': [unreg_user],
            'node_ids': [comp1._primary_key, comp2._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        self.app.post(url, json=payload, auth=self.creator.auth)

        # finalize_invitation should only have been called once
        assert mock_send_claim_email.call_count == 1

    @mock.patch('website.mails.send_mail')
    def test_add_contributors_post_only_sends_one_email_to_registered_user(self, mock_send_mail):
        # Project has components
        comp1 = NodeFactory(creator=self.creator, parent=self.project)
        comp2 = NodeFactory(creator=self.creator, parent=self.project)

        # A registered user is added to the project AND its components
        user = UserFactory()
        user_dict = {
            'id': user._id,
            'fullname': user.fullname,
            'email': user.username,
            'permission': permissions.WRITE,
            'visible': True}

        payload = {
            'users': [user_dict],
            'node_ids': [comp1._primary_key, comp2._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        self.app.post(url, json=payload, auth=self.creator.auth)

        # send_mail should only have been called once
        assert mock_send_mail.call_count == 1

    @mock.patch('website.mails.send_mail')
    def test_add_contributors_post_sends_email_if_user_not_contributor_on_parent_node(self, mock_send_mail):
        # Project has a component with a sub-component
        component = NodeFactory(creator=self.creator, parent=self.project)
        sub_component = NodeFactory(creator=self.creator, parent=component)

        # A registered user is added to the project and the sub-component, but NOT the component
        user = UserFactory()
        user_dict = {
            'id': user._id,
            'fullname': user.fullname,
            'email': user.username,
            'permission': permissions.WRITE,
            'visible': True}

        payload = {
            'users': [user_dict],
            'node_ids': [sub_component._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        self.app.post(url, json=payload, auth=self.creator.auth)

        # send_mail is called for both the project and the sub-component
        assert mock_send_mail.call_count == 2

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_email_sent_when_unreg_user_is_added(self, send_mail):
        name, email = fake.name(), fake_email()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': email,
            'permission': permissions.ADMIN,
            'visible': True,
        }
        payload = {
            'users': [pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        send_mail.assert_called_with(email, ANY,ANY,notify=True, email_template='default')

    @mock.patch('website.mails.send_mail')
    def test_email_sent_when_reg_user_is_added(self, send_mail):
        contributor = UserFactory()
        contributors = [{
            'user': contributor,
            'visible': True,
            'permissions': permissions.WRITE
        }]
        project = ProjectFactory(creator=self.auth.user)
        project.add_contributors(contributors, auth=self.auth)
        project.save()
        assert send_mail.called
        send_mail.assert_called_with(
            to_addr=contributor.username,
            mail=mails.CONTRIBUTOR_ADDED_DEFAULT,
            user=contributor,
            node=project,
            referrer_name=self.auth.user.fullname,
            all_global_subscriptions_none=False,
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            is_initiator=False,
            published_preprints=[]

        )
        assert contributor.contributor_added_email_records[project._id]['last_sent'] == approx(int(time.time()), rel=1)

    @mock.patch('website.mails.send_mail')
    def test_contributor_added_email_sent_to_unreg_user(self, send_mail):
        unreg_user = UnregUserFactory()
        project = ProjectFactory()
        project.add_unregistered_contributor(fullname=unreg_user.fullname, email=unreg_user.email, auth=Auth(project.creator))
        project.save()
        assert send_mail.called

    @mock.patch('website.mails.send_mail')
    def test_forking_project_does_not_send_contributor_added_email(self, send_mail):
        project = ProjectFactory()
        project.fork_node(auth=Auth(project.creator))
        assert not send_mail.called

    @mock.patch('website.mails.send_mail')
    def test_templating_project_does_not_send_contributor_added_email(self, send_mail):
        project = ProjectFactory()
        project.use_as_template(auth=Auth(project.creator))
        assert not send_mail.called

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('website.mails.send_mail')
    def test_registering_project_does_not_send_contributor_added_email(self, send_mail, mock_archive):
        project = ProjectFactory()
        provider = RegistrationProviderFactory()
        project.register_node(
            get_default_metaschema(),
            Auth(user=project.creator),
            DraftRegistrationFactory(branched_from=project),
            None,
            provider=provider
        )
        assert not send_mail.called

    @mock.patch('website.mails.send_mail')
    def test_notify_contributor_email_does_not_send_before_throttle_expires(self, send_mail):
        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        notify_added_contributor(project, contributor, auth)
        assert send_mail.called

        # 2nd call does not send email because throttle period has not expired
        notify_added_contributor(project, contributor, auth)
        assert send_mail.call_count == 1

    @mock.patch('website.mails.send_mail')
    def test_notify_contributor_email_sends_after_throttle_expires(self, send_mail):
        throttle = 0.5

        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        notify_added_contributor(project, contributor, auth, throttle=throttle)
        assert send_mail.called

        time.sleep(1)  # throttle period expires
        notify_added_contributor(project, contributor, auth, throttle=throttle)
        assert send_mail.call_count == 2

    @mock.patch('website.mails.send_mail')
    def test_add_contributor_to_fork_sends_email(self, send_mail):
        contributor = UserFactory()
        fork = self.project.fork_node(auth=Auth(self.creator))
        fork.add_contributor(contributor, auth=Auth(self.creator))
        fork.save()
        assert send_mail.called
        assert send_mail.call_count == 1

    @mock.patch('website.mails.send_mail')
    def test_add_contributor_to_template_sends_email(self, send_mail):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        template.add_contributor(contributor, auth=Auth(self.creator))
        template.save()
        assert send_mail.called
        assert send_mail.call_count == 1

    @mock.patch('website.mails.send_mail')
    def test_creating_fork_does_not_email_creator(self, send_mail):
        contributor = UserFactory()
        fork = self.project.fork_node(auth=Auth(self.creator))
        assert not send_mail.called

    @mock.patch('website.mails.send_mail')
    def test_creating_template_does_not_email_creator(self, send_mail):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        assert not send_mail.called

    def test_add_multiple_contributors_only_adds_one_log(self):
        n_logs_pre = self.project.logs.count()
        reg_user = UserFactory()
        name = fake.name()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': fake_email(),
            'permission': permissions.WRITE,
            'visible': True,
        }
        reg_dict = add_contributor_json(reg_user)
        reg_dict['permission'] = permissions.ADMIN
        reg_dict['visible'] = True
        payload = {
            'users': [reg_dict, pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        self.project.reload()
        assert self.project.logs.count() == n_logs_pre + 1

    def test_add_contribs_to_multiple_nodes(self):
        child = NodeFactory(parent=self.project, creator=self.creator)
        n_contributors_pre = child.contributors.count()
        reg_user = UserFactory()
        name, email = fake.name(), fake_email()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': email,
            'permission': permissions.ADMIN,
            'visible': True,
        }
        reg_dict = add_contributor_json(reg_user)
        reg_dict['permission'] = permissions.ADMIN
        reg_dict['visible'] = True
        payload = {
            'users': [reg_dict, pseudouser],
            'node_ids': [self.project._primary_key, child._primary_key]
        }
        url = f'/api/v1/project/{self.project._id}/contributors/'
        self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        child.reload()
        assert child.contributors.count() == n_contributors_pre + len(payload['users'])

    def tearDown(self):
        super().tearDown()
        contributor_added.disconnect(notify_added_contributor)


class TestUserInviteViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = f'/api/v1/project/{self.project._primary_key}/invite_contributor/'

    def test_invite_contributor_post_if_not_in_db(self):
        name, email = fake.name(), fake_email()
        res = self.app.post(
            self.invite_url,
            json={'fullname': name, 'email': email},
            auth=self.user.auth,
        )
        contrib = res.json['contributor']
        assert contrib['id'] is None
        assert contrib['fullname'] == name
        assert contrib['email'] == email

    def test_invite_contributor_post_if_unreg_already_in_db(self):
        # A n unreg user is added to a different project
        name, email = fake.name(), fake_email()
        project2 = ProjectFactory()
        unreg_user = project2.add_unregistered_contributor(fullname=name, email=email,
                                                           auth=Auth(project2.creator))
        project2.save()
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': email}, auth=self.user.auth)
        expected = add_contributor_json(unreg_user)
        expected['fullname'] = name
        expected['email'] = email
        assert res.json['contributor'] == expected

    def test_invite_contributor_post_if_email_already_registered(self):
        reg_user = UserFactory()
        name, email = fake.name(), reg_user.username
        # Tries to invite user that is already registered - this is now permitted.
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': email},
                                 auth=self.user.auth)
        contrib = res.json['contributor']
        assert contrib['id'] == reg_user._id
        assert contrib['fullname'] == name
        assert contrib['email'] == email

    def test_invite_contributor_post_if_user_is_already_contributor(self):
        unreg_user = self.project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=Auth(self.project.creator)
        )
        self.project.save()
        # Tries to invite unreg user that is already a contributor
        res = self.app.post(self.invite_url,
                                 json={'fullname': fake.name(), 'email': unreg_user.username},
                                 auth=self.user.auth)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_invite_contributor_with_no_email(self):
        name = fake.name()
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': None}, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        data = res.json
        assert data['status'] == 'success'
        assert data['contributor']['fullname'] == name
        assert data['contributor']['email'] is None
        assert not data['contributor']['registered']

    def test_invite_contributor_requires_fullname(self):
        res = self.app.post(self.invite_url,
                                 json={'email': 'brian@queen.com', 'fullname': ''}, auth=self.user.auth,
                                 )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_to_given_email(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        send_claim_email(email=given_email, unclaimed_user=unreg_user, node=project)

        send_mail.assert_called_with(
            given_email,
            mails.INVITE_DEFAULT,
            user=unreg_user,
            referrer=ANY,
            node=project,
            claim_url=ANY,
            email=unreg_user.email,
            fullname=unreg_user.fullname,
            branded_service=None,
            can_change_preferences=False,
            logo='osf_logo',
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_to_referrer(self, send_mail):
        project = ProjectFactory()
        referrer = project.creator
        given_email, real_email = fake_email(), fake_email()
        unreg_user = project.add_unregistered_contributor(fullname=fake.name(),
                                                          email=given_email, auth=Auth(
                                                              referrer)
                                                          )
        project.save()
        send_claim_email(email=real_email, unclaimed_user=unreg_user, node=project)

        assert send_mail.called
        # email was sent to referrer
        send_mail.assert_called_with(
            referrer.username,
            mails.FORWARD_INVITE,
            user=unreg_user,
            referrer=referrer,
            claim_url=unreg_user.get_claim_url(project._id, external=True),
            email=real_email.lower().strip(),
            fullname=unreg_user.get_unclaimed_record(project._id)['name'],
            node=project,
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_before_throttle_expires(self, send_mail):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        send_mail.reset_mock()
        # 2nd call raises error because throttle hasn't expired
        with pytest.raises(HTTPError):
            send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        assert not send_mail.called


@pytest.mark.enable_implicit_clean
class TestClaimViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        self.project_with_source_tag = ProjectFactory(creator=self.referrer, is_public=True)
        self.preprint_with_source_tag = PreprintFactory(creator=self.referrer, is_public=True)
        osf_source_tag, created = Tag.all_tags.get_or_create(name=OsfSourceTags.Osf.value, system=True)
        preprint_source_tag, created = Tag.all_tags.get_or_create(name=provider_source_tag(self.preprint_with_source_tag.provider._id, 'preprint'), system=True)
        self.project_with_source_tag.add_system_tag(osf_source_tag.name)
        self.preprint_with_source_tag.add_system_tag(preprint_source_tag.name)
        self.given_name = fake.name()
        self.given_email = fake_email()
        self.project_with_source_tag.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.preprint_with_source_tag.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.user = self.project.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_claim_user_already_registered_redirects_to_claim_user_registered(self, claim_email):
        name = fake.name()
        email = fake_email()

        # project contributor adds an unregistered contributor (without an email) on public project
        unregistered_user = self.project.add_unregistered_contributor(
            fullname=name,
            email=None,
            auth=Auth(user=self.referrer)
        )
        assert unregistered_user in self.project.contributors

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for('claim_user_post', uid='undefined')
        self.app.post(invite_url, json={
            'pk': unregistered_user._primary_key,
            'value': email
        })
        assert claim_email.call_count == 1

        # set unregistered record email since we are mocking send_claim_email()
        unclaimed_record = unregistered_user.get_unclaimed_record(self.project._primary_key)
        unclaimed_record.update({'email': email})
        unregistered_user.save()

        # unregistered user then goes and makes an account with same email, before claiming themselves as contributor
        UserFactory(username=email, fullname=name)

        # claim link for the now registered email is accessed while not logged in
        token = unregistered_user.get_unclaimed_record(self.project._primary_key)['token']
        claim_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/?token={token}'
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/verify/{token}/'
        assert res.status_code == 302
        assert claim_registered_url in res.headers.get('Location')

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_claim_user_already_registered_secondary_email_redirects_to_claim_user_registered(self, claim_email):
        name = fake.name()
        email = fake_email()
        secondary_email = fake_email()

        # project contributor adds an unregistered contributor (without an email) on public project
        unregistered_user = self.project.add_unregistered_contributor(
            fullname=name,
            email=None,
            auth=Auth(user=self.referrer)
        )
        assert unregistered_user in self.project.contributors

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for('claim_user_post', uid='undefined')
        self.app.post(invite_url, json={
            'pk': unregistered_user._primary_key,
            'value': secondary_email
        })
        assert claim_email.call_count == 1

        # set unregistered record email since we are mocking send_claim_email()
        unclaimed_record = unregistered_user.get_unclaimed_record(self.project._primary_key)
        unclaimed_record.update({'email': secondary_email})
        unregistered_user.save()

        # unregistered user then goes and makes an account with same email, before claiming themselves as contributor
        registered_user = UserFactory(username=email, fullname=name)
        registered_user.emails.create(address=secondary_email)
        registered_user.save()

        # claim link for the now registered email is accessed while not logged in
        token = unregistered_user.get_unclaimed_record(self.project._primary_key)['token']
        claim_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/?token={token}'
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/verify/{token}/'
        assert res.status_code == 302
        assert claim_registered_url in res.headers.get('Location')

    def test_claim_user_invited_with_no_email_posts_to_claim_form(self):
        given_name = fake.name()
        invited_user = self.project.add_unregistered_contributor(
            fullname=given_name,
            email=None,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

        url = invited_user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        })
        assert res.status_code == 400

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_claim_user_post_with_registered_user_id(self, send_mail):
        # registered user who is attempting to claim the unclaimed contributor
        reg_user = UserFactory()
        payload = {
            # pk of unreg user record
            'pk': self.user._primary_key,
            'claimerId': reg_user._primary_key
        }
        url = f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/'
        res = self.app.post(url, json=payload)

        # mail was sent
        assert send_mail.call_count == 2
        # ... to the correct address
        referrer_call = send_mail.call_args_list[0]
        claimer_call = send_mail.call_args_list[1]
        args, _ = referrer_call
        assert args[0] == self.referrer.username
        args, _ = claimer_call
        assert args[0] == reg_user.username

        # view returns the correct JSON
        assert res.json == {
            'status': 'success',
            'email': reg_user.username,
            'fullname': self.given_name,
        }

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_registered_email(self, mock_send_mail):
        reg_user = UserFactory()
        send_claim_registered_email(
            claimer=reg_user,
            unclaimed_user=self.user,
            node=self.project
        )
        assert mock_send_mail.call_count == 2
        first_call_args = mock_send_mail.call_args_list[0][0]
        assert first_call_args[0] == self.referrer.username
        second_call_args = mock_send_mail.call_args_list[1][0]
        assert second_call_args[0] == reg_user.username

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_registered_email_before_throttle_expires(self, mock_send_mail):
        reg_user = UserFactory()
        send_claim_registered_email(
            claimer=reg_user,
            unclaimed_user=self.user,
            node=self.project,
        )
        mock_send_mail.reset_mock()
        # second call raises error because it was called before throttle period
        with pytest.raises(HTTPError):
            send_claim_registered_email(
                claimer=reg_user,
                unclaimed_user=self.user,
                node=self.project,
            )
        assert not mock_send_mail.called

    @mock.patch('website.project.views.contributor.send_claim_registered_email')
    def test_claim_user_post_with_email_already_registered_sends_correct_email(
            self, send_claim_registered_email):
        reg_user = UserFactory()
        payload = {
            'value': reg_user.username,
            'pk': self.user._primary_key
        }
        url = self.project.api_url_for('claim_user_post', uid=self.user._id)
        self.app.post(url, json=payload)
        assert send_claim_registered_email.called

    def test_user_with_removed_unclaimed_url_claiming(self):
        """ Tests that when an unclaimed user is removed from a project, the
        unregistered user object does not retain the token.
        """
        self.project.remove_contributor(self.user, Auth(user=self.referrer))

        assert self.project._primary_key not in self.user.unclaimed_records.keys()

    def test_user_with_claim_url_cannot_claim_twice(self):
        """ Tests that when an unclaimed user is replaced on a project with a
        claimed user, the unregistered user object does not retain the token.
        """
        reg_user = AuthUserFactory()

        self.project.replace_contributor(self.user, reg_user)

        assert self.project._primary_key not in self.user.unclaimed_records.keys()

    def test_claim_user_form_redirects_to_password_confirm_page_if_user_is_logged_in(self):
        reg_user = AuthUserFactory()
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=reg_user.auth)
        assert res.status_code == 302
        res = self.app.get(url, auth=reg_user.auth, follow_redirects=True)
        token = self.user.get_unclaimed_record(self.project._primary_key)['token']
        expected = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token=token,
        )
        assert res.request.path == expected

    @mock.patch('framework.auth.cas.make_response_from_ticket')
    def test_claim_user_when_user_is_registered_with_orcid(self, mock_response_from_ticket):
        # TODO: check in qa url encoding
        token = self.user.get_unclaimed_record(self.project._primary_key)['token']
        url = f'/user/{self.user._id}/{self.project._id}/claim/verify/{token}/'
        # logged out user gets redirected to cas login
        res1 = self.app.get(url)
        assert res1.status_code == 302
        res = self.app.resolve_redirect(self.app.get(url))
        service_url = f'http://localhost{url}'
        expected = cas.get_logout_url(service_url=unquote_plus(cas.get_login_url(service_url=service_url)))
        assert res1.location == expected

        # user logged in with orcid automatically becomes a contributor
        orcid_user, validated_credentials, cas_resp = generate_external_user_with_resp(url)
        mock_response_from_ticket.return_value = authenticate(
            orcid_user,
            redirect(url)
        )
        orcid_user.set_unusable_password()
        orcid_user.save()

        # The request to OSF with CAS service ticket must not have cookie and/or auth.
        service_ticket = fake.md5()
        url_with_service_ticket = f'{url}?ticket={service_ticket}'
        res = self.app.get(url_with_service_ticket)
        # The response of this request is expected to be a 302 with `Location`.
        # And the redirect URL must equal to the originial service URL
        assert res.status_code == 302
        redirect_url = res.headers['Location']
        assert unquote_plus(redirect_url) == url
        # The response of this request is expected have the `Set-Cookie` header with OSF cookie.
        # And the cookie must belong to the ORCiD user.
        raw_set_cookie = res.headers['Set-Cookie']
        assert raw_set_cookie
        simple_cookie = SimpleCookie()
        simple_cookie.load(raw_set_cookie)
        cookie_dict = {key: value.value for key, value in simple_cookie.items()}
        osf_cookie = cookie_dict.get(settings.COOKIE_NAME, None)
        assert osf_cookie is not None
        user = OSFUser.from_cookie(osf_cookie)
        assert user._id == orcid_user._id
        # The ORCiD user must be different from the unregistered user created when the contributor was added
        assert user._id != self.user._id

        # Must clear the Flask g context manual and set the OSF cookie to context
        g.current_session = None
        self.app.set_cookie(settings.COOKIE_NAME, osf_cookie)
        res = self.app.resolve_redirect(res)
        assert res.status_code == 302
        assert self.project.is_contributor(orcid_user)
        assert self.project.url in res.headers.get('Location')

    def test_get_valid_form(self):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200

    def test_invalid_claim_form_raise_400(self):
        uid = self.user._primary_key
        pid = self.project._primary_key
        url = f'/user/{uid}/{pid}/claim/?token=badtoken'
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 400

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_with_valid_data(self, mock_update_search_nodes):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'login?service=' in location
        assert 'username' in location
        assert 'verification_key' in location
        assert self.project._primary_key in location

        self.user.reload()
        assert self.user.is_registered
        assert self.user.is_active
        assert self.project._primary_key not in self.user.unclaimed_records

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_removes_all_unclaimed_data(self, mock_update_search_nodes):
        # user has multiple unclaimed records
        p2 = ProjectFactory(creator=self.referrer)
        self.user.add_unclaimed_record(p2, referrer=self.referrer,
                                       given_name=fake.name())
        self.user.save()
        assert len(self.user.unclaimed_records.keys()) > 1  # sanity check
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'username': self.given_email,
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        })
        self.user.reload()
        assert self.user.unclaimed_records == {}

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_sets_fullname_to_given_name(self, mock_update_search_nodes):
        # User is created with a full name
        original_name = fake.name()
        unreg = UnregUserFactory(fullname=original_name)
        # User invited with a different name
        different_name = fake.name()
        new_user = self.project.add_unregistered_contributor(
            email=unreg.username,
            fullname=different_name,
            auth=Auth(self.project.creator),
        )
        self.project.save()
        # Goes to claim url
        claim_url = new_user.get_claim_url(self.project._id)
        self.app.post(claim_url, data={
            'username': unreg.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })
        unreg.reload()
        # Full name was set correctly
        assert unreg.fullname == different_name
        # CSL names were set correctly
        parsed_name = impute_names_model(different_name)
        assert unreg.given_name == parsed_name['given_name']
        assert unreg.family_name == parsed_name['family_name']

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_claim_user_post_returns_fullname(self, send_mail):
        url = f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/'
        res = self.app.post(
            url,
            auth=self.referrer.auth,
            json={
                'value': self.given_email,
                'pk': self.user._primary_key
            },
        )
        assert res.json['fullname'] == self.given_name
        assert send_mail.called

        send_mail.assert_called_with(
            self.given_email,
            mails.INVITE_DEFAULT,
            user=self.user,
            referrer=self.referrer,
            node=ANY,
            claim_url=ANY,
            email=self.user.email,
            fullname=self.user.fullname,
            branded_service=None,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            can_change_preferences=False,
            logo='osf_logo'
        )


    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_claim_user_post_if_email_is_different_from_given_email(self, send_mail):
        email = fake_email()  # email that is different from the one the referrer gave
        url = f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/'
        self.app.post(url, json={'value': email, 'pk': self.user._primary_key} )
        assert send_mail.called
        assert send_mail.call_count == 2
        call_to_invited = send_mail.mock_calls[0]
        call_to_invited.assert_called_with(to_addr=email)
        call_to_referrer = send_mail.mock_calls[1]
        call_to_referrer.assert_called_with(to_addr=self.given_email)

    def test_claim_url_with_bad_token_returns_400(self):
        url = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token='badtoken',
        )
        res = self.app.get(url, auth=self.referrer.auth)
        assert res.status_code == 400

    def test_cannot_claim_user_with_user_who_is_already_contributor(self):
        # user who is already a contirbutor to the project
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        # Claiming user goes to claim url, but contrib is already logged in
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(
            url,
            auth=contrib.auth, follow_redirects=True)
        # Response is a 400
        assert res.status_code == 400

    def test_claim_user_with_project_id_adds_corresponding_claimed_tag_to_user(self):
        assert OsfClaimedTags.Osf.value not in self.user.system_tags
        url = self.user.get_claim_url(self.project_with_source_tag._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        self.user.reload()
        assert OsfClaimedTags.Osf.value in self.user.system_tags

    def test_claim_user_with_preprint_id_adds_corresponding_claimed_tag_to_user(self):
        assert provider_claimed_tag(self.preprint_with_source_tag.provider._id, 'preprint') not in self.user.system_tags
        url = self.user.get_claim_url(self.preprint_with_source_tag._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        self.user.reload()
        assert provider_claimed_tag(self.preprint_with_source_tag.provider._id, 'preprint') in self.user.system_tags


@pytest.mark.enable_bookmark_creation
class TestPointerViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

    def _make_pointer_only_user_can_see(self, user, project, save=False):
        node = ProjectFactory(creator=user)
        project.add_pointer(node, auth=Auth(user=user), save=save)

    def test_pointer_list_write_contributor_can_remove_private_component_entry(self):
        """Ensure that write contributors see the button to delete a pointer,
            even if they cannot see what it is pointing at"""
        url = web_url_for('view_project', pid=self.project._id)
        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=permissions.DEFAULT_CONTRIBUTOR_PERMISSIONS)

        self._make_pointer_only_user_can_see(user2, self.project)
        self.project.save()

        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == 200

        has_controls = html.fromstring(res.text).xpath('//li[@node_id]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
        assert has_controls

    def test_pointer_list_write_contributor_can_remove_public_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)

        for i in range(3):
            self.project.add_pointer(ProjectFactory(creator=self.user),
                                     auth=Auth(user=self.user))
        self.project.save()

        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == 200
        has_controls = html.fromstring(res.text).xpath(
            '//div[@node_id]//i[contains(@class, "remove-pointer")]'
        )
        assert len(has_controls) == 3

    def test_pointer_list_read_contributor_cannot_remove_private_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)
        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=permissions.READ)

        self._make_pointer_only_user_can_see(user2, self.project)
        self.project.save()

        res = self.app.get(url, auth=user2.auth, follow_redirects=True)
        assert res.status_code == 200

        pointer_nodes = html.fromstring(res.text).xpath('//div[@node_id]')
        has_controls = html.fromstring(res.text).xpath('//div[@node_id]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
        assert len(pointer_nodes) == 1
        assert not has_controls

    def test_pointer_list_read_contributor_cannot_remove_public_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)

        self.project.add_pointer(ProjectFactory(creator=self.user,
                                                is_public=True),
                                 auth=Auth(user=self.user))

        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=permissions.READ)
        self.project.save()

        res = self.app.get(url, auth=user2.auth, follow_redirects=True)
        assert res.status_code == 200

        pointer_nodes = html.fromstring(res.text).xpath('//div[@node_id]')
        has_controls = html.fromstring(res.text).xpath(
            '//li[@node_id]//i[contains(@class, "remove-pointer")]')
        assert len(pointer_nodes) == 1
        assert len(has_controls) == 0

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1109
    def test_get_pointed_excludes_folders(self):
        pointer_project = ProjectFactory(is_public=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=self.user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        # Project is in an organizer collection
        collection = CollectionFactory(creator=pointed_project.creator)
        collection.collect_object(pointed_project, self.user)

        url = pointed_project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
        # pointer_project's id is included in response, but folder's id is not
        pointer_ids = [each['id'] for each in res.json['pointed']]
        assert pointer_project._id in pointer_ids
        assert collection._id not in pointer_ids

    def test_add_pointers(self):

        url = self.project.api_url + 'pointer/'
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        self.app.post(
            url,
            json={'nodeIds': node_ids},
            auth=self.user.auth,
            follow_redirects=True
        )

        self.project.reload()
        assert self.project.nodes_active.count() == 5

    def test_add_the_same_pointer_more_than_once(self):
        url = self.project.api_url + 'pointer/'
        double_node = NodeFactory()

        self.app.post(
            url,
            json={'nodeIds': [double_node._id]},
            auth=self.user.auth,
        )
        res = self.app.post(
            url,
            json={'nodeIds': [double_node._id]},
            auth=self.user.auth,
        )
        assert res.status_code == 400

    def test_add_pointers_no_user_logg_in(self):

        url = self.project.api_url_for('add_pointers')
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        res = self.app.post(
            url,
            json={'nodeIds': node_ids},
            auth=None,
        )

        assert res.status_code == 401

    def test_add_pointers_public_non_contributor(self):

        project2 = ProjectFactory()
        project2.set_privacy('public')
        project2.save()

        url = self.project.api_url_for('add_pointers')

        self.app.post(
            url,
            json={'nodeIds': [project2._id]},
            auth=self.user.auth,
            follow_redirects=True
        )

        self.project.reload()
        assert self.project.nodes_active.count() == 1

    def test_add_pointers_contributor(self):
        user2 = AuthUserFactory()
        self.project.add_contributor(user2)
        self.project.save()

        url = self.project.api_url_for('add_pointers')
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        self.app.post(
            url,
            json={'nodeIds': node_ids},
            auth=user2.auth,
            follow_redirects=True
        )

        self.project.reload()
        assert self.project.linked_nodes.count() == 5

    def test_add_pointers_not_provided(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.post(url, json={}, auth=self.user.auth)
        assert res.status_code == 400


    def test_remove_pointer(self):
        url = self.project.api_url + 'pointer/'
        node = NodeFactory()
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)
        self.app.delete(
            url,
            json={'pointerId': pointer.node._id},
            auth=self.user.auth,
        )
        self.project.reload()
        assert len(list(self.project.nodes)) == 0

    def test_remove_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete(url, json={}, auth=self.user.auth)
        assert res.status_code == 400

    def test_remove_pointer_not_found(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete(
            url,
            json={'pointerId': None},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_remove_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete(
            url,
            json={'pointerId': 'somefakeid'},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_forking_pointer_works(self):
        url = self.project.api_url + 'pointer/fork/'
        linked_node = NodeFactory(creator=self.user)
        pointer = self.project.add_pointer(linked_node, auth=self.consolidate_auth)
        assert linked_node.id == pointer.child.id
        res = self.app.post(url, json={'nodeId': pointer.child._id}, auth=self.user.auth)
        assert res.status_code == 201
        assert 'node' in res.json['data']
        fork = res.json['data']['node']
        assert fork['title'] == f'Fork of {linked_node.title}'

    def test_fork_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post(url, json={}, auth=self.user.auth,
                                 )
        assert res.status_code == 400

    def test_fork_pointer_not_found(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post(
            url,
            json={'nodeId': None},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_fork_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post(
            url,
            json={'nodeId': 'somefakeid'},
            auth=self.user.auth,

        )
        assert res.status_code == 400

    def test_before_register_with_pointer(self):
        # Assert that link warning appears in before register callback.
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert len(prompts) == 1

    def test_before_fork_with_pointer(self):
        """Assert that link warning appears in before fork callback."""
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'These links will be copied into your registration,' in prompt
        ]
        assert len(prompts) == 1

    def test_before_register_no_pointer(self):
        """Assert that link warning does not appear in before register callback."""
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert len(prompts) == 0

    def test_before_fork_no_pointer(self):
        """Assert that link warning does not appear in before fork callback."""
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your registration' in prompt
        ]
        assert len(prompts) == 0

    def test_get_pointed(self):
        pointing_node = ProjectFactory(creator=self.user)
        pointing_node.add_pointer(self.project, auth=Auth(self.user))
        url = self.project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        pointed = res.json['pointed']
        assert len(pointed) == 1
        assert pointed[0]['url'] == pointing_node.url
        assert pointed[0]['title'] == pointing_node.title
        assert pointed[0]['authorShort'] == abbrev_authors(pointing_node)

    def test_get_pointed_private(self):
        secret_user = UserFactory()
        pointing_node = ProjectFactory(creator=secret_user)
        pointing_node.add_pointer(self.project, auth=Auth(secret_user))
        url = self.project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        pointed = res.json['pointed']
        assert len(pointed) == 1
        assert pointed[0]['url'] is None
        assert pointed[0]['title'] == 'Private Component'
        assert pointed[0]['authorShort'] == 'Private Author(s)'

    def test_can_template_project_linked_to_each_other(self):
        project2 = ProjectFactory(creator=self.user)
        self.project.add_pointer(project2, auth=Auth(user=self.user))
        template = self.project.use_as_template(auth=Auth(user=self.user))

        assert template
        assert template.title == 'Templated from ' + self.project.title
        assert project2 not in template.linked_nodes


class TestPublicViews(OsfTestCase):

    def test_explore(self):
        res = self.app.get('/explore/', follow_redirects=True)
        assert res.status_code == 200


class TestAuthViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_ok(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.fullname == name
        assert user.accepted_terms_of_service is None

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2902
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_email_case_insensitive(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': str(email).upper(),
                'password': password,
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.fullname == name

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_email_with_accepted_tos(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
                'acceptedTermsOfService': True
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.accepted_terms_of_service

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_email_without_accepted_tos(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
                'acceptedTermsOfService': False
            }
        )
        user = OSFUser.objects.get(username=email)
        assert user.accepted_terms_of_service is None

    @mock.patch('framework.auth.views.send_confirm_email_async')
    def test_register_scrubs_username(self, _):
        url = api_url_for('register_user')
        name = "<i>Eunice</i> O' \"Cornwallis\"<script type='text/javascript' src='http://www.cornify.com/js/cornify.js'></script><script type='text/javascript'>cornify_add()</script>"
        email, password = fake_email(), 'underpressure'
        res = self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
            }
        )

        expected_scrub_username = "Eunice O' \"Cornwallis\"cornify_add()"
        user = OSFUser.objects.get(username=email)

        assert res.status_code == http_status.HTTP_200_OK
        assert user.fullname == expected_scrub_username

    def test_register_email_mismatch(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        res = self.app.post(
            url,
            json={
                'fullName': name,
                'email1': email,
                'email2': email + 'lol',
                'password': password,
            },
        )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST
        users = OSFUser.objects.filter(username=email)
        assert users.count() == 0

    def test_register_email_already_registered(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), fake.password()
        existing_user = UserFactory(
            username=email,
        )
        res = self.app.post(
            url, json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password
            },

        )
        assert res.status_code == http_status.HTTP_409_CONFLICT
        users = OSFUser.objects.filter(username=email)
        assert users.count() == 1

    def test_register_blocked_email_domain(self):
        NotableDomain.objects.get_or_create(
            domain='mailinator.com',
            note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT,
        )
        url = api_url_for('register_user')
        name, email, password = fake.name(), 'bad@mailinator.com', 'agreatpasswordobviously'
        res = self.app.post(
            url, json={
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password
            },

        )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST
        users = OSFUser.objects.filter(username=email)
        assert users.count() == 0

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=True)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_good_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        captcha = 'some valid captcha'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    'g-recaptcha-response': captcha,
                }
            )
            validate_recaptcha.assert_called_with(captcha, remote_ip='127.0.0.1')
            assert resp.status_code == http_status.HTTP_200_OK
            user = OSFUser.objects.get(username=email)
            assert user.fullname == name

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=False)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_missing_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    # 'g-recaptcha-response': 'supposed to be None',
                },
            )
            validate_recaptcha.assert_called_with(None, remote_ip='127.0.0.1')
            assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=False)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_bad_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    'g-recaptcha-response': 'bad captcha',
                },

            )
            assert resp.status_code == http_status.HTTP_400_BAD_REQUEST

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_register_after_being_invited_as_unreg_contributor(self, mock_update_search_nodes):
        # Regression test for:
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/861
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/1021
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/1026
        # A user is invited as an unregistered contributor
        project = ProjectFactory()

        name, email = fake.name(), fake_email()

        project.add_unregistered_contributor(fullname=name, email=email, auth=Auth(project.creator))
        project.save()

        # The new, unregistered user
        new_user = OSFUser.objects.get(username=email)

        # Instead of following the invitation link, they register at the regular
        # registration page

        # They use a different name when they register, but same email
        real_name = fake.name()
        password = 'myprecious'

        url = api_url_for('register_user')
        payload = {
            'fullName': real_name,
            'email1': email,
            'email2': email,
            'password': password,
        }
        # Send registration request
        self.app.post(url, json=payload)

        new_user.reload()

        # New user confirms by following confirmation link
        confirm_url = new_user.get_confirmation_url(email, external=False)
        self.app.get(confirm_url)

        new_user.reload()
        # Password and fullname should be updated
        assert new_user.is_confirmed
        assert new_user.check_password(password)
        assert new_user.fullname == real_name

    @mock.patch('framework.auth.views.send_confirm_email_async')
    def test_register_sends_user_registered_signal(self, mock_send_confirm_email_async):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with capture_signals() as mock_signals:
            self.app.post(
                url,
                json={
                    'fullName': name,
                    'email1': email,
                    'email2': email,
                    'password': password,
                }
            )
        assert mock_signals.signals_sent() == {auth.signals.user_registered, auth.signals.unconfirmed_user_created}
        assert mock_send_confirm_email_async.called

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation(self, send_mail: MagicMock):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert send_mail.called
        send_mail.assert_called_with(
            email,
            mails.CONFIRM_EMAIL,
            user=self.user,
            confirmation_url=ANY,
            email='test@mail.com',
            merge_target=None,
            external_id_provider=None,
            branded_preprints_provider=None,
            osf_support_email=settings.OSF_SUPPORT_EMAIL,
            can_change_preferences=False,
            logo='osf_logo'
        )
        self.user.reload()
        assert token != self.user.get_confirmation_token(email)
        with pytest.raises(InvalidTokenError):
            self.user.get_unconfirmed_email_for_token(token)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_click_confirmation_email(self, send_mail):
        # TODO: check in qa url encoding
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        res = self.app.get(url)
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == True
        assert res.status_code == 302
        login_url = quote_plus('login?service')
        assert login_url in res.text

    def test_get_email_to_add_no_email(self):
        email_verifications = self.user.unconfirmed_email_info
        assert email_verifications == []

    def test_get_unconfirmed_email(self):
        email = 'test@mail.com'
        self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        assert email_verifications == []

    def test_get_email_to_add(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == True
        email_verifications = self.user.unconfirmed_email_info
        assert email_verifications[0]['address'] == 'test@mail.com'

    def test_add_email(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put(put_email_url, json=email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert res.json['status'] == 'success'
        assert self.user.emails.last().address == 'test@mail.com'

    def test_remove_email(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        remove_email_url = api_url_for('unconfirmed_email_remove')
        remove_res = self.app.delete(remove_email_url, json=email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert remove_res.json['status'] == 'success'
        assert self.user.unconfirmed_email_info == []

    def test_add_expired_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.email_verifications[token]['expiration'] = timezone.now() - dt.timedelta(days=100)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['email'] == email
        self.user.clean_email_verifications(given_token=token)
        unconfirmed_emails = self.user.unconfirmed_email_info
        assert unconfirmed_emails == []
        assert self.user.email_verifications == {}

    def test_clean_email_verifications(self):
        # Do not return bad token and removes it from user.email_verifications
        email = 'test@mail.com'
        token = 'blahblahblah'
        self.user.email_verifications[token] = {'expiration': timezone.now() + dt.timedelta(days=1),
                                                'email': email,
                                                'confirmed': False }
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['email'] == email
        self.user.clean_email_verifications(given_token=token)
        unconfirmed_emails = self.user.unconfirmed_email_info
        assert unconfirmed_emails == []
        assert self.user.email_verifications == {}

    def test_clean_email_verifications_when_email_verifications_is_an_empty_dict(self):
        self.user.email_verifications = {}
        self.user.save()
        ret = self.user.clean_email_verifications()
        assert ret is None
        assert self.user.email_verifications == {}

    def test_add_invalid_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = '\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello@yourmom.com'
        # illegal_str = u'\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello'
        # illegal_str += unichr(0xd800) + unichr(0xdbff) + ' World'
        # email = 'test@mail.com'
        with pytest.raises(ValidationError):
            self.user.add_unconfirmed_email(email)

    def test_add_email_merge(self):
        email = 'copy@cat.com'
        dupe = UserFactory(
            username=email,
        )
        dupe.save()
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert self.user.email_verifications[token]['confirmed'] == False
        url = f'/confirm/{self.user._id}/{token}/?logout=1'
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put(put_email_url, json=email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert res.json['status'] == 'success'
        assert self.user.emails.last().address == 'copy@cat.com'

    def test_resend_confirmation_without_user_id(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        res = self.app.put(url, json={'email': header}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == '"id" is required'

    def test_resend_confirmation_without_email(self):
        url = api_url_for('resend_confirmation')
        res = self.app.put(url, json={'id': self.user._id}, auth=self.user.auth)
        assert res.status_code == 400

    def test_resend_confirmation_not_work_for_primary_email(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': True, 'confirmed': False}
        res = self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == 'Cannnot resend confirmation for confirmed emails'

    def test_resend_confirmation_not_work_for_confirmed_email(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': True}
        res = self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert res.status_code == 400
        assert res.json['message_long'] == 'Cannnot resend confirmation for confirmed emails'

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_does_not_send_before_throttle_expires(self, send_mail):
        email = 'test@mail.com'
        self.user.save()
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert send_mail.called
        # 2nd call does not send email because throttle period has not expired
        res = self.app.put(url, json={'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert res.status_code == 400

    def test_confirm_email_clears_unclaimed_records_and_revokes_token(self):
        unclaimed_user = UnconfirmedUserFactory()
        # unclaimed user has been invited to a project.
        referrer = UserFactory()
        project = ProjectFactory(creator=referrer)
        unclaimed_user.add_unclaimed_record(project, referrer, 'foo')
        unclaimed_user.save()

        # sanity check
        assert len(unclaimed_user.email_verifications.keys()) == 1

        # user goes to email confirmation link
        token = unclaimed_user.get_confirmation_token(unclaimed_user.username)
        url = web_url_for('confirm_email_get', uid=unclaimed_user._id, token=token)
        res = self.app.get(url)
        assert res.status_code == 302

        # unclaimed records and token are cleared
        unclaimed_user.reload()
        assert unclaimed_user.unclaimed_records == {}
        assert len(unclaimed_user.email_verifications.keys()) == 0

    def test_confirmation_link_registers_user(self):
        user = OSFUser.create_unconfirmed('brian@queen.com', 'bicycle123', 'Brian May')
        assert not user.is_registered  # sanity check
        user.save()
        confirmation_url = user.get_confirmation_url('brian@queen.com', external=False)
        res = self.app.get(confirmation_url)
        assert res.status_code == 302, 'redirects to settings page'
        res = self.app.get(confirmation_url, follow_redirects=True)
        user.reload()
        assert user.is_registered


class TestAuthLoginAndRegisterLogic(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.no_auth = Auth()
        self.user_auth = AuthUserFactory()
        self.auth = Auth(user=self.user_auth)
        self.next_url = web_url_for('my_projects', _absolute=True)
        self.invalid_campaign = 'invalid_campaign'

    def test_osf_login_with_auth(self):
        # login: user with auth
        data = login_and_register_handler(self.auth)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_osf_login_without_auth(self):
        # login: user without auth
        data = login_and_register_handler(self.no_auth)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_osf_register_with_auth(self):
        # register: user with auth
        data = login_and_register_handler(self.auth, login=False)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_osf_register_without_auth(self):
        # register: user without auth
        data = login_and_register_handler(self.no_auth, login=False)
        assert data.get('status_code') == http_status.HTTP_200_OK
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_next_url_login_with_auth(self):
        # next_url login: user with auth
        data = login_and_register_handler(self.auth, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == self.next_url

    def test_next_url_login_without_auth(self):
        # login: user without auth
        request.url = web_url_for('auth_login', next=self.next_url, _absolute=True)
        data = login_and_register_handler(self.no_auth, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(request.url)

    def test_next_url_register_with_auth(self):
        # register: user with auth
        data = login_and_register_handler(self.auth, login=False, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == self.next_url

    def test_next_url_register_without_auth(self):
        # register: user without auth
        data = login_and_register_handler(self.no_auth, login=False, next_url=self.next_url)
        assert data.get('status_code') == http_status.HTTP_200_OK
        assert data.get('next_url') == request.url

    def test_institution_login_and_register(self):
        pass

    def test_institution_login_with_auth(self):
        # institution login: user with auth
        data = login_and_register_handler(self.auth, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_institution_login_without_auth(self):
        # institution login: user without auth
        data = login_and_register_handler(self.no_auth, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(web_url_for('dashboard', _absolute=True),
                                                         campaign='institution')

    def test_institution_login_next_url_with_auth(self):
        # institution login: user with auth and next url
        data = login_and_register_handler(self.auth, next_url=self.next_url, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == self.next_url

    def test_institution_login_next_url_without_auth(self):
        # institution login: user without auth and next url
        data = login_and_register_handler(self.no_auth, next_url=self.next_url ,campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(self.next_url, campaign='institution')

    def test_institution_regsiter_with_auth(self):
        # institution register: user with auth
        data = login_and_register_handler(self.auth, login=False, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == web_url_for('dashboard', _absolute=True)

    def test_institution_register_without_auth(self):
        # institution register: user without auth
        data = login_and_register_handler(self.no_auth, login=False, campaign='institution')
        assert data.get('status_code') == http_status.HTTP_302_FOUND
        assert data.get('next_url') == cas.get_login_url(web_url_for('dashboard', _absolute=True), campaign='institution')

    def test_campaign_login_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user with auth
            data = login_and_register_handler(self.auth, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == campaign_url_for(campaign)

    def test_campaign_login_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user without auth
            data = login_and_register_handler(self.no_auth, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == web_url_for('auth_register', campaign=campaign,
                                                       next=campaign_url_for(campaign))

    def test_campaign_register_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user with auth
            data = login_and_register_handler(self.auth, login=False, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == campaign_url_for(campaign)

    def test_campaign_register_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user without auth
            data = login_and_register_handler(self.no_auth, login=False, campaign=campaign)
            assert data.get('status_code') == http_status.HTTP_200_OK
            if is_native_login(campaign):
                # native campaign: prereg and erpc
                assert data.get('next_url') == campaign_url_for(campaign)
            elif is_proxy_login(campaign):
                # proxy campaign: preprints and branded ones
                assert data.get('next_url') == web_url_for('auth_login', next=campaign_url_for(campaign),
                                                           _absolute=True)

    def test_campaign_next_url_login_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user with auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.auth, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == next_url

    def test_campaign_next_url_login_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user without auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.no_auth, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == web_url_for('auth_register', campaign=campaign, next=next_url)

    def test_campaign_next_url_register_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user with auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.auth, login=False, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_302_FOUND
            assert data.get('next_url') == next_url

    def test_campaign_next_url_register_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user without auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.no_auth, login=False, campaign=campaign, next_url=next_url)
            assert data.get('status_code') == http_status.HTTP_200_OK
            if is_native_login(campaign):
                # native campaign: prereg and erpc
                assert data.get('next_url') == next_url
            elif is_proxy_login(campaign):
                # proxy campaign: preprints and branded ones
                assert data.get('next_url') == web_url_for('auth_login', next= next_url, _absolute=True)

    def test_invalid_campaign_login_without_auth(self):
        data = login_and_register_handler(
            self.no_auth,
            login=True,
            campaign=self.invalid_campaign,
            next_url=self.next_url
        )
        redirect_url = web_url_for('auth_login', campaigns=None, next=self.next_url)
        assert data['status_code'] == http_status.HTTP_302_FOUND
        assert data['next_url'] == redirect_url
        assert data['campaign'] is None

    def test_invalid_campaign_register_without_auth(self):
        data = login_and_register_handler(
            self.no_auth,
            login=False,
            campaign=self.invalid_campaign,
            next_url=self.next_url
        )
        redirect_url = web_url_for('auth_register', campaigns=None, next=self.next_url)
        assert data['status_code'] == http_status.HTTP_302_FOUND
        assert data['next_url'] == redirect_url
        assert data['campaign'] is None

    # The following two tests handles the special case for `claim_user_registered`
    # When an authenticated user clicks the claim confirmation clink, there are two ways to trigger this flow:
    # 1. If the authenticated user is already a contributor to the project, OSF will ask the user to sign out
    #    by providing a "logout" link.
    # 2. If the authenticated user is not a contributor but decides not to claim contributor under this account,
    #    OSF provides a link "not <username>?" for the user to logout.
    # Both links will land user onto the register page with "MUST LOGIN" push notification.
    def test_register_logout_flag_with_auth(self):
        # when user click the "logout" or "not <username>?" link, first step is to log user out
        data = login_and_register_handler(self.auth, login=False, campaign=None, next_url=self.next_url, logout=True)
        assert data.get('status_code') == 'auth_logout'
        assert data.get('next_url') == self.next_url

    def test_register_logout_flage_without(self):
        # the second step is to land user on register page with "MUST LOGIN" warning
        data = login_and_register_handler(self.no_auth, login=False, campaign=None, next_url=self.next_url, logout=True)
        assert data.get('status_code') == http_status.HTTP_200_OK
        assert data.get('next_url') == self.next_url
        assert data.get('must_login_warning')


class TestAuthLogout(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.goodbye_url = web_url_for('goodbye', _absolute=True)
        self.redirect_url = web_url_for('forgot_password_get', _absolute=True)
        self.valid_next_url = web_url_for('dashboard', _absolute=True)
        self.invalid_next_url = 'http://localhost:1234/abcde'
        self.auth_user = AuthUserFactory()

    def tearDown(self):
        super().tearDown()
        OSFUser.objects.all().delete()
        assert OSFUser.objects.count() == 0

    def test_logout_with_valid_next_url_logged_in(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.valid_next_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(logout_url) == resp.headers['Location']

    def test_logout_with_valid_next_url_logged_out(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.valid_next_url)
        resp = self.app.get(logout_url, auth=None)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert self.valid_next_url == resp.headers['Location']

    def test_logout_with_invalid_next_url_logged_in(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.invalid_next_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.goodbye_url) == resp.headers['Location']

    def test_logout_with_invalid_next_url_logged_out(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.invalid_next_url)
        resp = self.app.get(logout_url, auth=None)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.goodbye_url) == resp.headers['Location']

    def test_logout_with_redirect_url(self):
        logout_url = web_url_for('auth_logout', _absolute=True, redirect_url=self.redirect_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.redirect_url) == resp.headers['Location']

    def test_logout_with_no_parameter(self):
        logout_url = web_url_for('auth_logout', _absolute=True)
        resp = self.app.get(logout_url, auth=None)
        assert resp.status_code == http_status.HTTP_302_FOUND
        assert cas.get_logout_url(self.goodbye_url) == resp.headers['Location']


class TestExternalAuthViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        name, email = fake.name(), fake_email()
        self.provider_id = fake.ean()
        external_identity = {
            'orcid': {
                self.provider_id: 'CREATE'
            }
        }
        password = str(fake.password())
        self.user = OSFUser.create_unconfirmed(
            username=email,
            password=password,
            fullname=name,
            external_identity=external_identity,
        )
        self.user.save()
        self.auth = (self.user.username, password)

    def test_external_login_email_get_with_invalid_session(self):
        url = web_url_for('external_login_email_get')
        resp = self.app.get(url)
        assert resp.status_code == 401

    def test_external_login_confirm_email_get_with_another_user_logged_in(self):
        # TODO: check in qa url encoding
        another_user = AuthUserFactory()
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url, auth=another_user.auth)
        assert res.status_code == 302, 'redirects to cas logout'
        assert '/logout?service=' in res.location
        assert quote_plus(url) in res.location

    def test_external_login_confirm_email_get_without_destination(self):
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid')
        res = self.app.get(url, auth=self.auth)
        assert res.status_code == 400, 'bad request'

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_create(self, mock_welcome):
        # TODO: check in qa url encoding
        assert not self.user.is_registered
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 302, 'redirects to cas login'
        assert '/login?service=' in res.location
        assert quote_plus('new=true') in res.location

        assert mock_welcome.call_count == 0

        self.user.reload()
        assert self.user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert self.user.is_registered
        assert self.user.has_usable_password()

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_link(self, mock_link_confirm):
        self.user.external_identity['orcid'][self.provider_id] = 'LINK'
        self.user.save()
        assert not self.user.is_registered
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 302, 'redirects to cas login'
        assert 'You should be redirected automatically' in str(res.html)
        assert '/login?service=' in res.location
        assert 'new=true' not in parse.unquote(res.location)

        assert mock_link_confirm.call_count == 1

        self.user.reload()
        assert self.user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert self.user.is_registered
        assert self.user.has_usable_password()

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_duped_id(self, mock_confirm):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert dupe_user.external_identity == self.user.external_identity
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 302, 'redirects to cas login'
        assert 'You should be redirected automatically' in str(res.html)
        assert '/login?service=' in res.location

        assert mock_confirm.call_count == 0

        self.user.reload()
        dupe_user.reload()

        assert self.user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert dupe_user.external_identity == {}

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_duping_id(self, mock_confirm):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'VERIFIED'}})
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 403, 'only allows one user to link an id'

        assert mock_confirm.call_count == 0

        self.user.reload()
        dupe_user.reload()

        assert dupe_user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert self.user.external_identity == {}

    def test_ensure_external_identity_uniqueness_unverified(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert dupe_user.external_identity == self.user.external_identity

        ensure_external_identity_uniqueness('orcid', self.provider_id, self.user)

        dupe_user.reload()
        self.user.reload()

        assert dupe_user.external_identity == {}
        assert self.user.external_identity == {'orcid': {self.provider_id: 'CREATE'}}

    def test_ensure_external_identity_uniqueness_verified(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'VERIFIED'}})
        assert dupe_user.external_identity == {'orcid': {self.provider_id: 'VERIFIED'}}
        assert dupe_user.external_identity != self.user.external_identity

        with pytest.raises(ValidationError):
            ensure_external_identity_uniqueness('orcid', self.provider_id, self.user)

        dupe_user.reload()
        self.user.reload()

        assert dupe_user.external_identity == {'orcid': {self.provider_id: 'VERIFIED'}}
        assert self.user.external_identity == {}

    def test_ensure_external_identity_uniqueness_multiple(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert dupe_user.external_identity == self.user.external_identity

        ensure_external_identity_uniqueness('orcid', self.provider_id)

        dupe_user.reload()
        self.user.reload()

        assert dupe_user.external_identity == {}
        assert self.user.external_identity == {}

# TODO: Use mock add-on
class TestAddonUserViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()

    def test_choose_addons_add(self):
        """Add add-ons; assert that add-ons are attached to project.

        """
        url = '/api/v1/settings/addons/'
        self.app.post(
            url,
            json={'github': True},
            auth=self.user.auth
        , follow_redirects=True)
        self.user.reload()
        assert self.user.get_addon('github')

    def test_choose_addons_remove(self):
        # Add, then delete, add-ons; assert that add-ons are not attached to
        # project.
        url = '/api/v1/settings/addons/'
        self.app.post(
            url,
            json={'github': True},
            auth=self.user.auth
        , follow_redirects=True)
        self.app.post(
            url,
            json={'github': False},
            auth=self.user.auth
        , follow_redirects=True)
        self.user.reload()
        assert not self.user.get_addon('github')


@pytest.mark.enable_enqueue_task
class TestConfigureMailingListViews(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._original_enable_email_subscriptions = settings.ENABLE_EMAIL_SUBSCRIPTIONS
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = True

    def test_user_unsubscribe_and_subscribe_help_mailing_list(self):
        user = AuthUserFactory()
        url = api_url_for('user_choose_mailing_lists')
        payload = {settings.OSF_HELP_LIST: False}
        res = self.app.post(url, json=payload, auth=user.auth)
        user.reload()

        assert not user.osf_mailing_lists[settings.OSF_HELP_LIST]

        payload = {settings.OSF_HELP_LIST: True}
        res = self.app.post(url, json=payload, auth=user.auth)
        user.reload()

        assert user.osf_mailing_lists[settings.OSF_HELP_LIST]

    def test_get_notifications(self):
        user = AuthUserFactory()
        mailing_lists = dict(list(user.osf_mailing_lists.items()) + list(user.mailchimp_mailing_lists.items()))
        url = api_url_for('user_notifications')
        res = self.app.get(url, auth=user.auth)
        assert mailing_lists == res.json['mailing_lists']

    def test_osf_help_mails_subscribe(self):
        user = UserFactory()
        user.osf_mailing_lists[settings.OSF_HELP_LIST] = False
        user.save()
        update_osf_help_mails_subscription(user, True)
        assert user.osf_mailing_lists[settings.OSF_HELP_LIST]

    def test_osf_help_mails_unsubscribe(self):
        user = UserFactory()
        user.osf_mailing_lists[settings.OSF_HELP_LIST] = True
        user.save()
        update_osf_help_mails_subscription(user, False)
        assert not user.osf_mailing_lists[settings.OSF_HELP_LIST]

    @unittest.skipIf(settings.USE_CELERY, 'Subscription must happen synchronously for this test')
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_user_choose_mailing_lists_updates_user_dict(self, mock_get_mailchimp_api):
        user = AuthUserFactory()
        list_name = MAILCHIMP_GENERAL_LIST
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': 1, 'list_name': list_name}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)

        payload = {settings.MAILCHIMP_GENERAL_LIST: True}
        url = api_url_for('user_choose_mailing_lists')
        res = self.app.post(url, json=payload, auth=user.auth)
        # the test app doesn't have celery handlers attached, so we need to call this manually.
        handlers.celery_teardown_request()
        user.reload()

        # check user.mailing_lists is updated
        assert user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST]
        assert user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST] == payload[settings.MAILCHIMP_GENERAL_LIST]

        # check that user is subscribed
        mock_client.lists.members.create_or_update.assert_called()

    def test_get_mailchimp_get_endpoint_returns_200(self):
        url = api_url_for('mailchimp_get_endpoint')
        res = self.app.get(url)
        assert res.status_code == 200

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_mailchimp_webhook_subscribe_action_does_not_change_user(self, mock_get_mailchimp_api):
        """ Test that 'subscribe' actions sent to the OSF via mailchimp
            webhooks update the OSF database.
        """
        list_id = '12345'
        list_name = MAILCHIMP_GENERAL_LIST
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': list_id, 'name': list_name}

        # user is not subscribed to a list
        user = AuthUserFactory()
        user.mailchimp_mailing_lists = {MAILCHIMP_GENERAL_LIST: False}
        user.save()

        # user subscribes and webhook sends request to OSF
        data = {
            'type': 'subscribe',
            'data[list_id]': list_id,
            'data[email]': user.username
        }
        url = api_url_for('sync_data_from_mailchimp') + '?key=' + settings.MAILCHIMP_WEBHOOK_SECRET_KEY
        res = self.app.post(url,
                            data=data,
                            content_type='application/x-www-form-urlencoded',
                            auth=user.auth)

        # user field is updated on the OSF
        user.reload()
        assert user.mailchimp_mailing_lists[list_name]

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_mailchimp_webhook_profile_action_does_not_change_user(self, mock_get_mailchimp_api):
        """ Test that 'profile' actions sent to the OSF via mailchimp
            webhooks do not cause any database changes.
        """
        list_id = '12345'
        list_name = 'OSF General'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': list_id, 'name': list_name}]}

        # user is subscribed to a list
        user = AuthUserFactory()
        user.mailchimp_mailing_lists = {'OSF General': True}
        user.save()

        # user hits subscribe again, which will update the user's existing info on mailchimp
        # webhook sends request (when configured to update on changes made through the API)
        data = {
            'type': 'profile',
            'data[list_id]': list_id,
            'data[email]': user.username
        }
        url = api_url_for('sync_data_from_mailchimp') + '?key=' + settings.MAILCHIMP_WEBHOOK_SECRET_KEY
        res = self.app.post(url,
                            data=data,
                            content_type='application/x-www-form-urlencoded',
                            auth=user.auth)

        # user field does not change
        user.reload()
        assert user.mailchimp_mailing_lists[list_name]

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_sync_data_from_mailchimp_unsubscribes_user(self, mock_get_mailchimp_api):
        list_id = '12345'
        list_name = 'OSF General'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.get.return_value = {'id': list_id, 'name': list_name}

        # user is subscribed to a list
        user = AuthUserFactory()
        user.mailchimp_mailing_lists = {'OSF General': True}
        user.save()

        # user unsubscribes through mailchimp and webhook sends request
        data = {
            'type': 'unsubscribe',
            'data[list_id]': list_id,
            'data[email]': user.username
        }
        url = api_url_for('sync_data_from_mailchimp') + '?key=' + settings.MAILCHIMP_WEBHOOK_SECRET_KEY
        res = self.app.post(url,
                            data=data,
                            content_type='application/x-www-form-urlencoded',
                            auth=user.auth)

        # user field is updated on the OSF
        user.reload()
        assert not user.mailchimp_mailing_lists[list_name]

    def test_sync_data_from_mailchimp_fails_without_secret_key(self):
        user = AuthUserFactory()
        payload = {'values': {'type': 'unsubscribe',
                              'data': {'list_id': '12345',
                                       'email': 'freddie@cos.io'}}}
        url = api_url_for('sync_data_from_mailchimp')
        res = self.app.post(url, json=payload, auth=user.auth)
        assert res.status_code == http_status.HTTP_401_UNAUTHORIZED

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = cls._original_enable_email_subscriptions

# TODO: Move to OSF Storage
class TestFileViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=True)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_grid_data(self):
        url = self.project.api_url_for('grid_data')
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == http_status.HTTP_200_OK
        expected = rubeus.to_hgrid(self.project, auth=Auth(self.user))
        data = res.json['data']
        assert len(data) == len(expected)


class TestTagViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    @unittest.skip('Tags endpoint disabled for now.')
    def test_tag_get_returns_200(self):
        url = web_url_for('project_tag', tag='foo')
        res = self.app.get(url)
        assert res.status_code == 200


class TestReorderComponents(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.contrib = AuthUserFactory()
        # Project is public
        self.project = ProjectFactory.create(creator=self.creator, is_public=True)
        self.project.add_contributor(self.contrib, auth=Auth(self.creator))

        # subcomponent that only creator can see
        self.public_component = NodeFactory(creator=self.creator, is_public=True)
        self.private_component = NodeFactory(creator=self.creator, is_public=False)
        NodeRelation.objects.create(parent=self.project, child=self.public_component)
        NodeRelation.objects.create(parent=self.project, child=self.private_component)

        self.project.save()

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_reorder_components_with_private_component(self):

        # contrib tries to reorder components
        payload = {
            'new_list': [
                f'{self.private_component._id}',
                f'{self.public_component._id}',
            ]
        }
        url = self.project.api_url_for('project_reorder_components')
        res = self.app.post(url, json=payload, auth=self.contrib.auth)
        assert res.status_code == 200


class TestWikiWidgetViews(OsfTestCase):

    def setUp(self):
        super().setUp()

        # project with no home wiki page
        self.project = ProjectFactory()
        self.read_only_contrib = AuthUserFactory()
        self.project.add_contributor(self.read_only_contrib, permissions=permissions.READ)
        self.noncontributor = AuthUserFactory()

        # project with no home wiki content
        self.project2 = ProjectFactory(creator=self.project.creator)
        self.project2.add_contributor(self.read_only_contrib, permissions=permissions.READ)
        WikiPage.objects.create_for_node(self.project2, 'home', '', Auth(self.project.creator))

    def test_show_wiki_for_contributors_when_no_wiki_or_content(self):
        assert _should_show_wiki_widget(self.project, self.project.creator)
        assert _should_show_wiki_widget(self.project2, self.project.creator)

    def test_show_wiki_is_false_for_read_contributors_when_no_wiki_or_content(self):
        assert not _should_show_wiki_widget(self.project, self.read_only_contrib)
        assert not _should_show_wiki_widget(self.project2, self.read_only_contrib)

    def test_show_wiki_is_false_for_noncontributors_when_no_wiki_or_content(self):
        assert not _should_show_wiki_widget(self.project, None)

    def test_show_wiki_for_osf_group_members(self):
        group = OSFGroupFactory(creator=self.noncontributor)
        self.project.add_osf_group(group, permissions.READ)
        assert not _should_show_wiki_widget(self.project, self.noncontributor)
        assert not _should_show_wiki_widget(self.project2, self.noncontributor)

        self.project.remove_osf_group(group)
        self.project.add_osf_group(group, permissions.WRITE)
        assert _should_show_wiki_widget(self.project, self.noncontributor)
        assert not _should_show_wiki_widget(self.project2, self.noncontributor)


@pytest.mark.enable_implicit_clean
@pytest.mark.enable_bookmark_creation
class TestProjectCreation(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.url = api_url_for('project_new_post')
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user1)
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()

    def tearDown(self):
        super().tearDown()

    def test_needs_title(self):
        res = self.app.post(self.url, json={}, auth=self.creator.auth)
        assert res.status_code == 400

    def test_create_component_strips_html(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        url = web_url_for('project_new_node', pid=project._id)
        post_data = {'title': '<b>New <blink>Component</blink> Title</b>', 'category': ''}
        self.app.post(url, data=post_data, auth=user.auth, follow_redirects=True)
        project.reload()
        child = project.nodes[0]
        # HTML has been stripped
        assert child.title == 'New Component Title'

    def test_strip_html_from_title(self):
        payload = {
            'title': 'no html <b>here</b>'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert 'no html here' == node.title

    def test_only_needs_title(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201

    def test_title_must_be_one_long(self):
        payload = {
            'title': ''
        }
        res = self.app.post(
            self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 400

    def test_title_must_be_less_than_200(self):
        payload = {
            'title': ''.join([str(x) for x in range(0, 250)])
        }
        res = self.app.post(
            self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 400

    def test_fails_to_create_project_with_whitespace_title(self):
        payload = {
            'title': '   '
        }
        res = self.app.post(
            self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 400

    def test_creates_a_project(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert node.title == 'Im a real title'

    def test_create_component_add_contributors_admin(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, data=post_data, auth=self.user1.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert self.user1 in child.contributors
        assert self.user2 in child.contributors
        # check redirect url
        assert '/contributors/' in res.location

    def test_create_component_with_contributors_read_write(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        read_user = AuthUserFactory()
        group = OSFGroupFactory(creator=read_user)
        self.project.add_contributor(non_admin, permissions=permissions.WRITE)
        self.project.add_contributor(read_user, permissions=permissions.READ)
        self.project.add_osf_group(group, permissions.ADMIN)
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, data=post_data, auth=non_admin.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert non_admin in child.contributors
        assert self.user1 in child.contributors
        assert self.user2 in child.contributors
        assert read_user in child.contributors
        assert child.has_permission(non_admin, permissions.ADMIN) is True
        assert child.has_permission(non_admin, permissions.WRITE) is True
        assert child.has_permission(non_admin, permissions.READ) is True
        # read_user was a read contrib on the parent, but was an admin group member
        # read contrib perms copied over
        assert child.has_permission(read_user, permissions.ADMIN) is False
        assert child.has_permission(read_user, permissions.WRITE) is False
        assert child.has_permission(read_user, permissions.READ) is True
        # User creating the component was not a manager on the group
        assert group not in child.osf_groups
        # check redirect url
        assert '/contributors/' in res.location

    def test_group_copied_over_to_component_if_manager(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        write_user = AuthUserFactory()
        group = OSFGroupFactory(creator=write_user)
        self.project.add_contributor(non_admin, permissions=permissions.WRITE)
        self.project.add_contributor(write_user, permissions=permissions.WRITE)
        self.project.add_osf_group(group, permissions.ADMIN)
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, data=post_data, auth=write_user.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert non_admin in child.contributors
        assert self.user1 in child.contributors
        assert self.user2 in child.contributors
        assert write_user in child.contributors
        assert child.has_permission(non_admin, permissions.ADMIN) is False
        assert child.has_permission(non_admin, permissions.WRITE) is True
        assert child.has_permission(non_admin, permissions.READ) is True
        # Component creator gets admin
        assert child.has_permission(write_user, permissions.ADMIN) is True
        assert child.has_permission(write_user, permissions.WRITE) is True
        assert child.has_permission(write_user, permissions.READ) is True
        # User creating the component was a manager of the group, so group copied
        assert group in child.osf_groups
        # check redirect url
        assert '/contributors/' in res.location

    def test_create_component_with_contributors_read(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=permissions.READ)
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, json=post_data, auth=non_admin.auth)
        assert res.status_code == 403

    def test_create_component_add_no_contributors(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        post_data = {'title': 'New Component With Contributors Title', 'category': ''}
        res = self.app.post(url, data=post_data, auth=self.user1.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert child.title == 'New Component With Contributors Title'
        assert self.user1 in child.contributors
        assert self.user2 not in child.contributors
        # check redirect url
        assert '/contributors/' not in res.location

    def test_new_project_returns_serialized_node_data(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = res.json['newNode']
        assert node
        assert node['title'] == 'Im a real title'

    def test_description_works(self):
        payload = {
            'title': 'Im a real title',
            'description': 'I describe things!'
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert node.description == 'I describe things!'

    def test_can_template(self):
        other_node = ProjectFactory(creator=self.creator)
        payload = {
            'title': 'Im a real title',
            'template': other_node._id
        }
        res = self.app.post(self.url, json=payload, auth=self.creator.auth)
        assert res.status_code == 201
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert node
        assert node.template_node == other_node

    def test_project_before_template_no_addons(self):
        project = ProjectFactory()
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert res.json['prompts'] == []

    def test_project_before_template_with_addons(self):
        project = ProjectWithAddonFactory(addon='box')
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert 'Box' in res.json['prompts']

    def test_project_new_from_template_non_user(self):
        project = ProjectFactory()
        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=None)
        assert res.status_code == 302
        res2 = self.app.resolve_redirect(res)
        assert res2.status_code == 308
        assert res2.request.path == '/login'

    def test_project_new_from_template_public_non_contributor(self):
        non_contributor = AuthUserFactory()
        project = ProjectFactory(is_public=True)
        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=non_contributor.auth)
        assert res.status_code == 201

    def test_project_new_from_template_contributor(self):
        contributor = AuthUserFactory()
        project = ProjectFactory(is_public=False)
        project.add_contributor(contributor)
        project.save()

        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=contributor.auth)
        assert res.status_code == 201


class TestUnconfirmedUserViews(OsfTestCase):

    def test_can_view_profile(self):
        user = UnconfirmedUserFactory()
        url = web_url_for('profile_view_id', uid=user._id)
        res = self.app.get(url)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

class TestStaticFileViews(OsfTestCase):

    def test_robots_dot_txt(self):
        res = self.app.get('/robots.txt')
        assert res.status_code == 200
        assert 'User-agent' in res.text
        assert 'html' in res.headers['Content-Type']

    def test_favicon(self):
        res = self.app.get('/favicon.ico')
        assert res.status_code == 200
        assert 'image/vnd.microsoft.icon' in res.headers['Content-Type']

    def test_getting_started_page(self):
        res = self.app.get('/getting-started/')
        assert res.status_code == 302
        assert res.location == 'https://help.osf.io/article/342-getting-started-on-the-osf'
    def test_help_redirect(self):
        res = self.app.get('/help/')
        assert res.status_code == 302


class TestUserConfirmSignal(OsfTestCase):

    def test_confirm_user_signal_called_when_user_claims_account(self):
        unclaimed_user = UnconfirmedUserFactory()
        # unclaimed user has been invited to a project.
        referrer = UserFactory()
        project = ProjectFactory(creator=referrer)
        unclaimed_user.add_unclaimed_record(project, referrer, 'foo', email=fake_email())
        unclaimed_user.save()

        token = unclaimed_user.get_unclaimed_record(project._primary_key)['token']
        with capture_signals() as mock_signals:
            url = web_url_for('claim_user_form', pid=project._id, uid=unclaimed_user._id, token=token)
            payload = {'username': unclaimed_user.username,
                       'password': 'password',
                       'password2': 'password'}
            res = self.app.post(url, data=payload)
            assert res.status_code == 302

        assert mock_signals.signals_sent() == {auth.signals.user_confirmed}

    def test_confirm_user_signal_called_when_user_confirms_email(self):
        unconfirmed_user = UnconfirmedUserFactory()
        unconfirmed_user.save()

        # user goes to email confirmation link
        token = unconfirmed_user.get_confirmation_token(unconfirmed_user.username)
        with capture_signals() as mock_signals:
            url = web_url_for('confirm_email_get', uid=unconfirmed_user._id, token=token)
            res = self.app.get(url)
            assert res.status_code == 302

        assert mock_signals.signals_sent() == {auth.signals.user_confirmed}


# copied from tests/test_comments.py
class TestCommentViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.project = ProjectFactory(is_public=True)
        self.user = AuthUserFactory()
        self.project.add_contributor(self.user)
        self.project.save()
        self.user.save()

    def test_view_project_comments_updates_user_comments_view_timestamp(self):
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put(url, json={
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[self.project._id]
        view_timestamp = timezone.now()
        assert_datetime_equal(user_timestamp, view_timestamp)

    def test_confirm_non_contrib_viewers_dont_have_pid_in_comments_view_timestamp(self):
        non_contributor = AuthUserFactory()
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put(url, json={
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)

        non_contributor.reload()
        assert self.project._id not in non_contributor.comments_viewed_timestamp

    def test_view_comments_updates_user_comments_view_timestamp_files(self):
        osfstorage = self.project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        test_file = root_node.append_file('test_file')
        test_file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()

        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put(url, json={
            'page': 'files',
            'rootId': test_file._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[test_file._id]
        view_timestamp = timezone.now()
        assert_datetime_equal(user_timestamp, view_timestamp)

        # Regression test for https://openscience.atlassian.net/browse/OSF-5193
        # moved from tests/test_comments.py
        def test_find_unread_includes_edited_comments(self):
            project = ProjectFactory()
            user = AuthUserFactory()
            project.add_contributor(user, save=True)
            comment = CommentFactory(node=project, user=project.creator)
            n_unread = Comment.find_n_unread(user=user, node=project, page='node')
            assert n_unread == 1

            url = project.api_url_for('update_comments_timestamp')
            payload = {'page': 'node', 'rootId': project._id}
            self.app.put(url, json=payload, auth=user.auth)
            user.reload()
            n_unread = Comment.find_n_unread(user=user, node=project, page='node')
            assert n_unread == 0

            # Edit previously read comment
            comment.edit(
                auth=Auth(project.creator),
                content='edited',
                save=True
            )
            n_unread = Comment.find_n_unread(user=user, node=project, page='node')
            assert n_unread == 1


class TestResetPassword(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.another_user = AuthUserFactory()
        self.osf_key_v2 = core.generate_verification_key(verification_type='password')
        self.user.verification_key_v2 = self.osf_key_v2
        self.user.verification_key = None
        self.user.save()
        self.get_url = web_url_for(
            'reset_password_get',
            uid=self.user._id,
            token=self.osf_key_v2['token']
        )
        self.get_url_invalid_key = web_url_for(
            'reset_password_get',
            uid=self.user._id,
            token=core.generate_verification_key()
        )
        self.get_url_invalid_user = web_url_for(
            'reset_password_get',
            uid=self.another_user._id,
            token=self.osf_key_v2['token']
        )

    # successfully load reset password page
    def test_reset_password_view_returns_200(self):
        res = self.app.get(self.get_url)
        assert res.status_code == 200

    # raise http 400 error
    def test_reset_password_view_raises_400(self):
        res = self.app.get(self.get_url_invalid_key)
        assert res.status_code == 400

        res = self.app.get(self.get_url_invalid_user)
        assert res.status_code == 400

        self.user.verification_key_v2['expires'] = timezone.now()
        self.user.save()
        res = self.app.get(self.get_url)
        assert res.status_code == 400

    # successfully reset password
    @pytest.mark.enable_enqueue_task
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_can_reset_password_if_form_success(self, mock_service_validate):
        # TODO: check in qa url encoding
        # load reset password page and submit email
        res = self.app.get(self.get_url)
        form = res.get_form('resetPasswordForm')
        form['password'] = 'newpassword'
        form['password2'] = 'newpassword'
        res = form.submit(self.app)

        # check request URL is /resetpassword with username and new verification_key_v2 token
        request_url_path = res.request.path
        assert 'resetpassword' in request_url_path
        assert self.user._id in request_url_path
        assert self.user.verification_key_v2['token'] not in request_url_path

        # check verification_key_v2 for OSF is destroyed and verification_key for CAS is in place
        self.user.reload()
        assert self.user.verification_key_v2 == {}
        assert not self.user.verification_key is None

        # check redirection to CAS login with username and the new verification_key(CAS)
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'login?service=' in location
        assert f'username={quote_plus(self.user.username)}' in location
        assert f'verification_key={self.user.verification_key}' in location

        # check if password was updated
        self.user.reload()
        assert self.user.check_password('newpassword')

        # check if verification_key is destroyed after service validation
        mock_service_validate.return_value = cas.CasResponse(
            authenticated=True,
            user=self.user._id,
            attributes={'accessToken': fake.md5()}
        )
        ticket = fake.md5()
        service_url = 'http://accounts.osf.io/?ticket=' + ticket
        with run_celery_tasks():
            cas.make_response_from_ticket(ticket, service_url)
        self.user.reload()
        assert self.user.verification_key is None

    #  log users out before they land on reset password page
    def test_reset_password_logs_out_user(self):
        # visit reset password link while another user is logged in
        res = self.app.get(self.get_url, auth=self.another_user.auth)
        # check redirection to CAS logout
        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'reauth' not in location
        assert 'logout?service=' in location
        assert 'resetpassword' in location


@mock.patch('website.views.PROXY_EMBER_APPS', False)
class TestResolveGuid(OsfTestCase):
    def setUp(self):
        super().setUp()

    @mock.patch('website.views.use_ember_app')
    def test_preprint_provider_without_domain(self, mock_use_ember_app):
        provider = PreprintProviderFactory(domain='')
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        mock_use_ember_app.assert_called_with()

    @mock.patch('website.views.use_ember_app')
    def test_preprint_provider_with_domain_without_redirect(self, mock_use_ember_app):
        domain = 'https://test.com/'
        provider = PreprintProviderFactory(_id='test', domain=domain, domain_redirect_enabled=False)
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        mock_use_ember_app.assert_called_with()

    def test_preprint_provider_with_domain_with_redirect(self):
        domain = 'https://test.com/'
        provider = PreprintProviderFactory(_id='test', domain=domain, domain_redirect_enabled=True)
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)

        assert_is_redirect(res)
        assert res.status_code == 301
        assert res.headers['location'] == f'{domain}{preprint._id}/'
        assert res.request.path == f'/{preprint._id}/'



    @mock.patch('website.views.use_ember_app')
    def test_preprint_provider_with_osf_domain(self, mock_use_ember_app):
        provider = PreprintProviderFactory(_id='osf', domain='https://osf.io/')
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        mock_use_ember_app.assert_called_with()


class TestConfirmationViewBlockBingPreview(OsfTestCase):

    def setUp(self):

        super().setUp()
        self.user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534+ (KHTML, like Gecko) BingPreview/1.0b'

    # reset password link should fail with BingPreview
    def test_reset_password_get_returns_403(self):

        user = UserFactory()
        osf_key_v2 = core.generate_verification_key(verification_type='password')
        user.verification_key_v2 = osf_key_v2
        user.verification_key = None
        user.save()

        reset_password_get_url = web_url_for(
            'reset_password_get',
            uid=user._id,
            token=osf_key_v2['token']
        )
        res = self.app.get(
            reset_password_get_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # new user confirm account should fail with BingPreview
    def test_confirm_email_get_new_user_returns_403(self):

        user = OSFUser.create_unconfirmed('unconfirmed@cos.io', 'abCD12#$', 'Unconfirmed User')
        user.save()
        confirm_url = user.get_confirmation_url('unconfirmed@cos.io', external=False)
        res = self.app.get(
            confirm_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for adding new email should fail with BingPreview
    def test_confirm_email_add_email_returns_403(self):

        user = UserFactory()
        user.add_unconfirmed_email('unconfirmed@cos.io')
        user.save()

        confirm_url = user.get_confirmation_url('unconfirmed@cos.io', external=False) + '?logout=1'
        res = self.app.get(
            confirm_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for merging accounts should fail with BingPreview
    def test_confirm_email_merge_account_returns_403(self):

        user = UserFactory()
        user_to_be_merged = UserFactory()
        user.add_unconfirmed_email(user_to_be_merged.username)
        user.save()

        confirm_url = user.get_confirmation_url(user_to_be_merged.username, external=False) + '?logout=1'
        res = self.app.get(
            confirm_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for new user claiming contributor should fail with BingPreview
    def test_claim_user_form_new_user(self):

        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        project.save()

        claim_url = user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # confirmation for existing user claiming contributor should fail with BingPreview
    def test_claim_user_form_existing_user(self):

        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        auth_user = AuthUserFactory()
        pending_user = project.add_unregistered_contributor(
            fullname=auth_user.fullname,
            email=None,
            auth=Auth(user=referrer)
        )
        project.save()
        claim_url = pending_user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            auth = auth_user.auth,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # account creation confirmation for ORCiD login should fail with BingPreview
    def test_external_login_confirm_email_get_create_user(self):
        name, email = fake.name(), fake_email()
        provider_id = fake.ean()
        external_identity = {
            'service': {
                provider_id: 'CREATE'
            }
        }
        user = OSFUser.create_unconfirmed(
            username=email,
            password=str(fake.password()),
            fullname=name,
            external_identity=external_identity,
        )
        user.save()
        create_url = user.get_confirmation_url(
            user.username,
            external_id_provider='service',
            destination='dashboard'
        )

        res = self.app.get(
            create_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403

    # account linking confirmation for ORCiD login should fail with BingPreview
    def test_external_login_confirm_email_get_link_user(self):

        user = UserFactory()
        provider_id = fake.ean()
        user.external_identity = {
            'service': {
                provider_id: 'LINK'
            }
        }
        user.add_unconfirmed_email(user.username, external_identity='service')
        user.save()

        link_url = user.get_confirmation_url(
            user.username,
            external_id_provider='service',
            destination='dashboard'
        )

        res = self.app.get(
            link_url,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert res.status_code == 403


if __name__ == '__main__':
    unittest.main()
