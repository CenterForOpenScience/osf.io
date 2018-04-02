#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Views tests for the OSF."""

from __future__ import absolute_import

import datetime as dt
import httplib as http
import json
import time
import unittest
import urllib

from flask import request
import mock
import pytest
from nose.tools import *  # noqa PEP8 asserts
from django.utils import timezone
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext

from addons.github.tests.factories import GitHubAccountFactory
from framework.auth import cas
from framework.auth.core import generate_verification_key
from framework import auth
from framework.auth.campaigns import get_campaigns, is_institution_login, is_native_login, is_proxy_login, campaign_url_for
from framework.auth import Auth
from framework.auth.cas import get_login_url
from framework.auth.exceptions import InvalidTokenError
from framework.auth.utils import impute_names_model, ensure_external_identity_uniqueness
from framework.auth.views import login_and_register_handler
from framework.celery_tasks import handlers
from framework.exceptions import HTTPError
from framework.transactions.handlers import no_auto_transaction
from website import mailchimp_utils, mails, settings, language
from addons.osfstorage import settings as osfstorage_settings
from osf.models import AbstractNode, NodeLog, QuickFilesNode
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.profile.views import fmt_date_or_none, update_osf_help_mails_subscription
from website.project.decorators import check_can_access
from website.project.model import has_anonymous_link
from website.project.signals import contributor_added
from website.project.views.contributor import (
    deserialize_contributors,
    notify_added_contributor,
    send_claim_email,
    send_claim_registered_email,
)
from website.project.views.node import _should_show_wiki_widget, _view_project, abbrev_authors
from website.util import api_url_for, web_url_for
from website.util import rubeus
from website.views import index
from osf.utils import permissions
from osf.models import Comment
from osf.models import OSFUser
from tests.base import (
    assert_is_redirect,
    capture_signals,
    fake,
    get_default_metaschema,
    OsfTestCase,
    assert_datetime_equal,
)
from tests.base import test_app as mock_app
from api_tests.utils import create_test_file

pytestmark = pytest.mark.django_db

from osf.models import NodeRelation, QuickFilesNode
from osf_tests.factories import (
    fake_email,
    ApiOAuth2ApplicationFactory,
    ApiOAuth2PersonalTokenFactory,
    AuthUserFactory,
    CollectionFactory,
    CommentFactory,
    InstitutionFactory,
    NodeFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PrivateLinkFactory,
    ProjectFactory,
    ProjectWithAddonFactory,
    RegistrationFactory,
    UserFactory,
    UnconfirmedUserFactory,
    UnregUserFactory,
)

@mock_app.route('/errorexc')
def error_exc():
    UserFactory()
    raise RuntimeError

@mock_app.route('/error500')
def error500():
    UserFactory()
    return 'error', 500

@mock_app.route('/noautotransact')
@no_auto_transaction
def no_auto_transact():
    UserFactory()
    return 'error', 500

class TestViewsAreAtomic(OsfTestCase):
    def test_error_response_rolls_back_transaction(self):
        original_user_count = OSFUser.objects.count()
        self.app.get('/error500', expect_errors=True)
        assert_equal(OSFUser.objects.count(), original_user_count)

        # Need to set debug = False in order to rollback transactions in transaction_teardown_request
        mock_app.debug = False
        try:
            self.app.get('/errorexc', expect_errors=True)
        except RuntimeError:
            pass
        mock_app.debug = True

        self.app.get('/noautotransact', expect_errors=True)
        assert_equal(OSFUser.objects.count(), original_user_count + 1)


class TestViewingProjectWithPrivateLink(OsfTestCase):

    def setUp(self):
        super(TestViewingProjectWithPrivateLink, self).setUp()
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
        res = self.app.put_json(url, {'pk': link._id, 'value': ''}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Title cannot be blank', res.body)

    def test_edit_private_link_invalid(self):
        node = ProjectFactory(creator=self.user)
        link = PrivateLinkFactory()
        link.nodes.add(node)
        link.save()
        url = node.api_url_for('project_private_link_edit')
        res = self.app.put_json(url, {'pk': link._id, 'value': '<a></a>'}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Invalid link name.', res.body)

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
        assert_true(has_anonymous_link(self.project, auth))

    def test_has_private_link_key(self):
        res = self.app.get(self.project_url, {'view_only': self.link.key})
        assert_equal(res.status_code, 200)

    def test_not_logged_in_no_key(self):
        res = self.app.get(self.project_url, {'view_only': None})
        assert_is_redirect(res)
        res = res.follow(expect_errors=True)
        assert_equal(res.status_code, 301)
        assert_equal(
            res.request.path,
            '/login'
        )

    def test_logged_in_no_private_key(self):
        res = self.app.get(self.project_url, {'view_only': None}, auth=self.user.auth,
                           expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_logged_in_has_key(self):
        res = self.app.get(
            self.project_url, {'view_only': self.link.key}, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    @unittest.skip('Skipping for now until we find a way to mock/set the referrer')
    def test_prepare_private_key(self):
        res = self.app.get(self.project_url, {'key': self.link.key})

        res = res.click('Registrations')

        assert_is_redirect(res)
        res = res.follow()

        assert_equal(res.status_code, 200)
        assert_equal(res.request.GET['key'], self.link.key)

    def test_cannot_access_registrations_or_forks_with_anon_key(self):
        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.add(self.project)
        anonymous_link.save()
        self.project.is_public = False
        self.project.save()
        url = self.project_url + 'registrations/?view_only={}'.format(anonymous_link.key)
        res = self.app.get(url, expect_errors=True)

        assert_equal(res.status_code, 401)

        url = self.project_url + 'forks/?view_only={}'.format(anonymous_link.key)

        res = self.app.get(url, expect_errors=True)

        assert_equal(res.status_code, 401)

    def test_can_access_registrations_and_forks_with_not_anon_key(self):
        link = PrivateLinkFactory(anonymous=False)
        link.nodes.add(self.project)
        link.save()
        self.project.is_public = False
        self.project.save()
        url = self.project_url + 'registrations/?view_only={}'.format(self.link.key)
        res = self.app.get(url)

        assert_equal(res.status_code, 200)

        url = self.project_url + 'forks/?view_only={}'.format(self.link.key)
        res = self.app.get(url)

        assert_equal(res.status_code, 200)

    def test_check_can_access_valid(self):
        contributor = AuthUserFactory()
        self.project.add_contributor(contributor, auth=Auth(self.project.creator))
        self.project.save()
        assert_true(check_can_access(self.project, contributor))

    def test_check_user_access_invalid(self):
        noncontrib = AuthUserFactory()
        with assert_raises(HTTPError):
            check_can_access(self.project, noncontrib)

    def test_check_user_access_if_user_is_None(self):
        assert_false(check_can_access(self.project, None))


class TestProjectViews(OsfTestCase):

    def setUp(self):
        super(TestProjectViews, self).setUp()
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
        assert_equal(res.status_code, 200)

        # user is automatically affiliated with institutions
        # that matched email domains
        user.reload()
        assert_in(inst1, user.affiliated_institutions.all())
        assert_in(inst2, user.affiliated_institutions.all())

    def test_edit_title_empty(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('edit_node')
        res = self.app.post_json(url, {'name': 'title', 'value': ''}, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Title cannot be blank', res.body)

    def test_edit_title_invalid(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('edit_node')
        res = self.app.post_json(url, {'name': 'title', 'value': '<a></a>'}, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Invalid title.', res.body)

    def test_view_project_doesnt_select_for_update(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for('view_project')

        with transaction.atomic(), CaptureQueriesContext(connection) as ctx:
            res = self.app.get(url, auth=self.user1.auth)

        for_update_sql = connection.ops.for_update_sql()
        assert_equal(res.status_code, 200)
        assert not any(for_update_sql in query['sql'] for query in ctx.captured_queries)

    def test_cannot_remove_only_visible_contributor(self):
        user1_contrib = self.project.contributor_set.get(user=self.user1)
        user1_contrib.visible = False
        user1_contrib.save()
        url = self.project.api_url_for('project_remove_contributor')
        res = self.app.post_json(
            url, {'contributorID': self.user2._id,
                  'nodeIDs': [self.project._id]}, auth=self.auth, expect_errors=True
        )
        assert_equal(res.status_code, http.FORBIDDEN)
        assert_equal(res.json['message_long'], 'Must have at least one bibliographic contributor')
        assert_true(self.project.is_contributor(self.user2))

    def test_remove_only_visible_contributor_return_false(self):
        user1_contrib = self.project.contributor_set.get(user=self.user1)
        user1_contrib.visible = False
        user1_contrib.save()
        ret = self.project.remove_contributor(contributor=self.user2, auth=self.consolidate_auth1)
        assert_false(ret)
        self.project.reload()
        assert_true(self.project.is_contributor(self.user2))

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
        assert_not_in('Private Project', res.body)
        assert_in('parent project', res.body)

    def test_edit_description(self):
        url = '/api/v1/project/{0}/edit/'.format(self.project._id)
        self.app.post_json(url,
                           {'name': 'description', 'value': 'Deep-fried'},
                           auth=self.auth)
        self.project.reload()
        assert_equal(self.project.description, 'Deep-fried')

    def test_project_api_url(self):
        url = self.project.api_url
        res = self.app.get(url, auth=self.auth)
        data = res.json
        assert_equal(data['node']['category'], 'Project')
        assert_equal(data['node']['node_type'], 'project')

        assert_equal(data['node']['title'], self.project.title)
        assert_equal(data['node']['is_public'], self.project.is_public)
        assert_equal(data['node']['is_registration'], False)
        assert_equal(data['node']['id'], self.project._primary_key)
        assert_true(data['user']['is_contributor'])
        assert_equal(data['node']['description'], self.project.description)
        assert_equal(data['node']['url'], self.project.url)
        assert_equal(data['node']['tags'], list(self.project.tags.values_list('name', flat=True)))
        assert_in('forked_date', data['node'])
        assert_in('registered_from_url', data['node'])
        # TODO: Test "parent" and "user" output

    def test_add_contributor_post(self):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        user2 = UserFactory()
        user3 = UserFactory()
        url = '/api/v1/project/{0}/contributors/'.format(project._id)

        dict2 = add_contributor_json(user2)
        dict3 = add_contributor_json(user3)
        dict2.update({
            'permission': 'admin',
            'visible': True,
        })
        dict3.update({
            'permission': 'write',
            'visible': False,
        })

        self.app.post_json(
            url,
            {
                'users': [dict2, dict3],
                'node_ids': [project._id],
            },
            content_type='application/json',
            auth=self.auth,
        ).maybe_follow()
        project.reload()
        assert_in(user2, project.contributors)
        # A log event was added
        assert_equal(project.logs.latest().action, 'contributor_added')
        assert_equal(len(project.contributors), 3)

        assert_equal(project.get_permissions(user2), ['read', 'write', 'admin'])
        assert_equal(project.get_permissions(user3), ['read', 'write'])

    def test_manage_permissions(self):
        url = self.project.api_url + 'contributors/manage/'
        self.app.post_json(
            url,
            {
                'contributors': [
                    {'id': self.project.creator._id, 'permission': 'admin',
                        'registered': True, 'visible': True},
                    {'id': self.user1._id, 'permission': 'read',
                        'registered': True, 'visible': True},
                    {'id': self.user2._id, 'permission': 'admin',
                        'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        self.project.reload()

        assert_equal(self.project.get_permissions(self.user1), ['read'])
        assert_equal(self.project.get_permissions(self.user2), ['read', 'write', 'admin'])

    def test_manage_permissions_again(self):
        url = self.project.api_url + 'contributors/manage/'
        self.app.post_json(
            url,
            {
                'contributors': [
                    {'id': self.user1._id, 'permission': 'admin',
                     'registered': True, 'visible': True},
                    {'id': self.user2._id, 'permission': 'admin',
                     'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        self.project.reload()
        self.app.post_json(
            url,
            {
                'contributors': [
                    {'id': self.user1._id, 'permission': 'admin',
                     'registered': True, 'visible': True},
                    {'id': self.user2._id, 'permission': 'read',
                     'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        self.project.reload()

        assert_equal(self.project.get_permissions(self.user2), ['read'])
        assert_equal(self.project.get_permissions(self.user1), ['read', 'write', 'admin'])

    def test_contributor_manage_reorder(self):

        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {'user': reg_user1, 'permissions': [
                    'read', 'write', 'admin'], 'visible': True},
                {'user': reg_user2, 'permissions': [
                    'read', 'write', 'admin'], 'visible': False},
            ]
        )
        # Add a non-registered user
        unregistered_user = project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=self.consolidate_auth1,
            save=True,
        )

        url = project.api_url + 'contributors/manage/'
        self.app.post_json(
            url,
            {
                'contributors': [
                    {'id': reg_user2._id, 'permission': 'admin',
                        'registered': True, 'visible': False},
                    {'id': project.creator._id, 'permission': 'admin',
                        'registered': True, 'visible': True},
                    {'id': unregistered_user._id, 'permission': 'admin',
                        'registered': False, 'visible': True},
                    {'id': reg_user1._id, 'permission': 'admin',
                        'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        project.reload()

        assert_equal(
            # Note: Cast ForeignList to list for comparison
            list(project.contributors),
            [reg_user2, project.creator, unregistered_user, reg_user1]
        )

        assert_equal(
            list(project.visible_contributors),
            [project.creator, unregistered_user, reg_user1]
        )

    def test_project_remove_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.project._id]}
        self.app.post(url, json.dumps(payload),
                      content_type='application/json',
                      auth=self.auth).maybe_follow()
        self.project.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs.latest().action, 'contributor_removed')

    def test_multiple_project_remove_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user2._id,
                   'nodeIDs': [self.project._id, self.project2._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type='application/json',
                            auth=self.auth).maybe_follow()
        self.project.reload()
        self.project2.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        assert_not_in('/dashboard/', res.json)

        assert_not_in(self.user2._id, self.project2.contributors)
        # A log event was added
        assert_equal(self.project.logs.latest().action, 'contributor_removed')

    def test_private_project_remove_self_not_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # user2 removes self
        payload = {"contributorID": self.user2._id,
                   "nodeIDs": [self.project._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type="application/json",
                            auth=self.auth2).maybe_follow()
        self.project.reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json['redirectUrl'], '/dashboard/')
        assert_not_in(self.user2._id, self.project.contributors)

    def test_public_project_remove_self_not_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # user2 removes self
        self.public_project = ProjectFactory(creator=self.user1, is_public=True)
        self.public_project.add_contributor(self.user2, auth=Auth(self.user1))
        self.public_project.save()
        payload = {"contributorID": self.user2._id,
                   "nodeIDs": [self.public_project._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type="application/json",
                            auth=self.auth2).maybe_follow()
        self.public_project.reload()
        assert_equal(res.status_code, 200)
        assert_equal(res.json['redirectUrl'], '/' + self.public_project._id + '/')
        assert_not_in(self.user2._id, self.public_project.contributors)

    def test_project_remove_other_not_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {"contributorID": self.user1._id,
                   "nodeIDs": [self.project._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type="application/json",
                            expect_errors=True,
                            auth=self.auth2).maybe_follow()
        self.project.reload()
        assert_equal(res.status_code, 403)
        assert_equal(res.json['message_long'],
                     'You do not have permission to perform this action. '
                     'If this should not have occurred and the issue persists, '
                     + language.SUPPORT_LINK
                     )
        assert_in(self.user1, self.project.contributors)

    def test_project_remove_fake_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': 'badid',
                   'nodeIDs': [self.project._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type='application/json',
                            expect_errors=True,
                            auth=self.auth).maybe_follow()
        self.project.reload()
        # Assert the contributor id was invalid
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Contributor not found.')
        assert_not_in('badid', self.project.contributors)

    def test_project_remove_self_only_admin(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {'contributorID': self.user1._id,
                   'nodeIDs': [self.project._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type='application/json',
                            expect_errors=True,
                            auth=self.auth).maybe_follow()

        self.project.reload()
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Could not remove contributor.')
        assert_in(self.user1, self.project.contributors)

    def test_get_contributors_abbrev(self):
        # create a project with 3 registered contributors
        project = ProjectFactory(creator=self.user1, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {'user': reg_user1, 'permissions': [
                    'read', 'write', 'admin'], 'visible': True},
                {'user': reg_user2, 'permissions': [
                    'read', 'write', 'admin'], 'visible': True},
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
        assert_equal(len(project.contributors), 4)
        assert_equal(len(res.json['contributors']), 3)
        assert_equal(len(res.json['others_count']), 1)
        assert_equal(res.json['contributors'][0]['separator'], ',')
        assert_equal(res.json['contributors'][1]['separator'], ',')
        assert_equal(res.json['contributors'][2]['separator'], ' &')

    def test_edit_node_title(self):
        url = '/api/v1/project/{0}/edit/'.format(self.project._id)
        # The title is changed though posting form data
        self.app.post_json(url, {'name': 'title', 'value': 'Bacon'},
                           auth=self.auth).maybe_follow()
        self.project.reload()
        # The title was changed
        assert_equal(self.project.title, 'Bacon')
        # A log event was saved
        assert_equal(self.project.logs.latest().action, 'edit_title')

    def test_add_tag(self):
        url = self.project.api_url_for('project_add_tag')
        self.app.post_json(url, {'tag': "foo'ta#@%#%^&g?"}, auth=self.auth)
        self.project.reload()
        assert_in("foo'ta#@%#%^&g?", self.project.tags.values_list('name', flat=True))
        assert_equal("foo'ta#@%#%^&g?", self.project.logs.latest().params['tag'])

    def test_remove_tag(self):
        self.project.add_tag("foo'ta#@%#%^&g?", auth=self.consolidate_auth1, save=True)
        assert_in("foo'ta#@%#%^&g?", self.project.tags.values_list('name', flat=True))
        url = self.project.api_url_for('project_remove_tag')
        self.app.delete_json(url, {'tag': "foo'ta#@%#%^&g?"}, auth=self.auth)
        self.project.reload()
        assert_not_in("foo'ta#@%#%^&g?", self.project.tags.values_list('name', flat=True))
        latest_log = self.project.logs.latest()
        assert_equal('tag_removed', latest_log.action)
        assert_equal("foo'ta#@%#%^&g?", latest_log.params['tag'])

    # Regression test for #OSF-5257
    def test_removal_empty_tag_throws_error(self):
        url = self.project.api_url_for('project_remove_tag')
        res = self.app.delete_json(url, {'tag': ''}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    # Regression test for #OSF-5257
    def test_removal_unknown_tag_throws_error(self):
        self.project.add_tag('narf', auth=self.consolidate_auth1, save=True)
        url = self.project.api_url_for('project_remove_tag')
        res = self.app.delete_json(url, {'tag': 'troz'}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, http.CONFLICT)

    def test_suspended_project(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        node.remove_node(Auth(self.user1))
        node.suspended = True
        node.save()
        url = node.api_url
        res = self.app.get(url, auth=Auth(self.user1), expect_errors=True)
        assert_equal(res.status_code, 451)

    def test_private_link_edit_name(self):
        link = PrivateLinkFactory(name='link')
        link.nodes.add(self.project)
        link.save()
        assert_equal(link.name, 'link')
        url = self.project.api_url + 'private_link/edit/'
        self.app.put_json(
            url,
            {'pk': link._id, 'value': 'new name'},
            auth=self.auth,
        ).maybe_follow()
        self.project.reload()
        link.reload()
        assert_equal(link.name, 'new name')

    def test_remove_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete_json(
            url,
            {'private_link_id': link._id},
            auth=self.auth,
        ).maybe_follow()
        self.project.reload()
        link.reload()
        assert_true(link.is_deleted)

    def test_remove_private_link_log(self):
        link = PrivateLinkFactory()
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete_json(
            url,
            {'private_link_id': link._id},
            auth=self.auth,
        ).maybe_follow()

        last_log = self.project.logs.latest()
        assert last_log.action == NodeLog.VIEW_ONLY_LINK_REMOVED
        assert not last_log.params.get('anonymous_link')

    def test_remove_private_link_anonymous_log(self):
        link = PrivateLinkFactory(anonymous=True)
        link.nodes.add(self.project)
        link.save()
        url = self.project.api_url_for('remove_private_link')
        self.app.delete_json(
            url,
            {'private_link_id': link._id},
            auth=self.auth,
        ).maybe_follow()

        last_log = self.project.logs.latest()
        assert last_log.action == NodeLog.VIEW_ONLY_LINK_REMOVED
        assert last_log.params.get('anonymous_link')

    def test_remove_component(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        url = node.api_url
        res = self.app.delete_json(url, {}, auth=self.auth).maybe_follow()
        node.reload()
        assert_equal(node.is_deleted, True)
        assert_in('url', res.json)
        assert_equal(res.json['url'], self.project.url)

    def test_cant_remove_component_if_not_admin(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        non_admin = AuthUserFactory()
        node.add_contributor(
            non_admin,
            permissions=['read', 'write'],
            save=True,
        )

        url = node.api_url
        res = self.app.delete_json(
            url, {}, auth=non_admin.auth,
            expect_errors=True,
        ).maybe_follow()

        assert_equal(res.status_code, http.FORBIDDEN)
        assert_false(node.is_deleted)

    def test_view_project_returns_whether_to_show_wiki_widget(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user, is_public=True)
        project.add_contributor(user)
        project.save()

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('show_wiki_widget', res.json['user'])

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
        assert_equal(grand_child_fork.root, fork)

    def test_fork_count_does_not_include_deleted_forks(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        fork = project.fork_node(auth)
        project.save()
        fork.remove_node(auth)
        fork.save()

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert_in('fork_count', res.json['node'])
        assert_equal(0, res.json['node']['fork_count'])

    def test_fork_count_does_not_include_fork_registrations(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        auth = Auth(project.creator)
        fork = project.fork_node(auth)
        project.save()
        registration = RegistrationFactory(project=fork)

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert_in('fork_count', res.json['node'])
        assert_equal(1, res.json['node']['fork_count'])

    def test_registration_retraction_redirect(self):
        url = self.project.web_url_for('node_registration_retraction_redirect')
        res = self.app.get(url, auth=self.auth)
        assert_equal(res.status_code, 302)
        assert_in(self.project.web_url_for('node_registration_retraction_get', _guid=True), res.location)

    def test_update_node(self):
        url = self.project.api_url_for('update_node')
        res = self.app.put_json(url, {'title': 'newtitle'}, auth=self.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(self.project.title, 'newtitle')

    # Regression test
    def test_update_node_with_tags(self):
        self.project.add_tag('cheezebørger', auth=Auth(self.project.creator), save=True)
        url = self.project.api_url_for('update_node')
        res = self.app.put_json(url, {'title': 'newtitle'}, auth=self.auth)
        assert_equal(res.status_code, 200)
        self.project.reload()
        assert_equal(self.project.title, 'newtitle')

    # Regression test
    def test_retraction_view(self):
        project = ProjectFactory(creator=self.user1, is_public=True)

        registration = RegistrationFactory(project=project, is_public=True)
        registration.retract_registration(self.user1)

        approval_token = registration.retraction.approval_state[self.user1._id]['approval_token']
        registration.retraction.approve_retraction(self.user1, approval_token)
        registration.save()

        url = registration.web_url_for('view_project')
        res = self.app.get(url, auth=self.auth)

        assert_not_in('Mako Runtime Error', res.body)
        assert_in(registration.title, res.body)
        assert_equal(res.status_code, 200)

        for route in ['files', 'wiki/home', 'analytics', 'forks', 'contributors', 'settings', 'withdraw', 'register', 'register/fakeid']:
            res = self.app.get('{}{}/'.format(url, route), auth=self.auth, allow_redirects=True)
            assert_equal(res.status_code, 302, route)
            res = res.follow()
            assert_equal(res.status_code, 200, route)
            assert_in('This project is a withdrawn registration of', res.body, route)


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
        assert_equal(len(self.project_results['children']), 4)
        assert_equal(self.project_results['node']['id'], self.project._id)

    def test_editable_children_order(self):
        assert_equal(self.project_results['children'][0]['id'], self.child._id)
        assert_equal(self.project_results['children'][1]['id'], self.grandchild._id)
        assert_equal(self.project_results['children'][2]['id'], self.great_grandchild._id)
        assert_equal(self.project_results['children'][3]['id'], self.great_great_grandchild._id)

    def test_editable_children_indents(self):
        assert_equal(self.project_results['children'][0]['indent'], 0)
        assert_equal(self.project_results['children'][1]['indent'], 1)
        assert_equal(self.project_results['children'][2]['indent'], 2)
        assert_equal(self.project_results['children'][3]['indent'], 3)

    def test_editable_children_parents(self):
        assert_equal(self.project_results['children'][0]['parent_id'], self.project._id)
        assert_equal(self.project_results['children'][1]['parent_id'], self.child._id)
        assert_equal(self.project_results['children'][2]['parent_id'], self.grandchild._id)
        assert_equal(self.project_results['children'][3]['parent_id'], self.great_grandchild._id)

    def test_editable_children_privacy(self):
        assert_false(self.project_results['node']['is_public'])
        assert_true(self.project_results['children'][0]['is_public'])
        assert_false(self.project_results['children'][1]['is_public'])
        assert_true(self.project_results['children'][2]['is_public'])
        assert_false(self.project_results['children'][3]['is_public'])

    def test_editable_children_titles(self):
        assert_equal(self.project_results['node']['title'], self.project.title)
        assert_equal(self.project_results['children'][0]['title'], self.child.title)
        assert_equal(self.project_results['children'][1]['title'], self.grandchild.title)
        assert_equal(self.project_results['children'][2]['title'], self.great_grandchild.title)
        assert_equal(self.project_results['children'][3]['title'], self.great_great_grandchild.title)


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
        assert_equal(node_id, project._primary_key)

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

        assert_equal(parent_node_id, project._primary_key)
        assert_in(child1._primary_key, child_ids)
        assert_in(child2._primary_key, child_ids)
        assert_in(child3._primary_key, child_ids)

    def test_get_node_with_child_linked_to_parent(self):
        project = ProjectFactory(creator=self.user)
        child1 = NodeFactory(parent=project, creator=self.user)
        child1.add_pointer(project, Auth(self.user))
        child1.save()
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        child1_id = tree['children'][0]['node']['id']
        assert_equal(child1_id, child1._primary_key)

    def test_get_node_not_parent_owner(self):
        project = ProjectFactory(creator=self.user2)
        child = NodeFactory(parent=project, creator=self.user2)
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json, [])

    # Parent node should show because of user2 read access, the children should not
    def test_get_node_parent_not_admin(self):
        project = ProjectFactory(creator=self.user)
        project.add_contributor(self.user2, auth=Auth(self.user))
        project.save()
        child1 = NodeFactory(parent=project, creator=self.user)
        child2 = NodeFactory(parent=project, creator=self.user)
        child3 = NodeFactory(parent=project, creator=self.user)
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user2.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        children = tree['children']
        assert_equal(parent_node_id, project._primary_key)
        assert_equal(children, [])


class TestUserProfile(OsfTestCase):

    def setUp(self):
        super(TestUserProfile, self).setUp()
        self.user = AuthUserFactory()

    def test_fmt_date_or_none(self):
        with assert_raises(HTTPError) as cm:
            #enter a date before 1900
            fmt_date_or_none(dt.datetime(1890, 10, 31, 18, 23, 29, 227))
        # error should be raised because date is before 1900
        assert_equal(cm.exception.code, http.BAD_REQUEST)

    def test_unserialize_social(self):
        url = api_url_for('unserialize_social')
        payload = {
            'profileWebsites': ['http://frozen.pizza.com/reviews'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
        }
        self.app.put_json(
            url,
            payload,
            auth=self.user.auth,
        )
        self.user.reload()
        for key, value in payload.iteritems():
            assert_equal(self.user.social[key], value)
        assert_true(self.user.social['researcherId'] is None)

    # Regression test for help-desk ticket
    def test_making_email_primary_is_not_case_sensitive(self):
        user = AuthUserFactory(username='fred@queen.test')
        # make confirmed email have different casing
        email = user.emails.first()
        email.address = email.address.capitalize()
        email.save()
        url = api_url_for('update_user')
        res = self.app.put_json(
            url,
            {'id': user._id, 'emails': [{'address': 'fred@queen.test', 'primary': True, 'confirmed': True}]},
            auth=user.auth
        )
        assert_equal(res.status_code, 200)

    def test_unserialize_social_validation_failure(self):
        url = api_url_for('unserialize_social')
        # profileWebsites URL is invalid
        payload = {
            'profileWebsites': ['http://goodurl.com', 'http://invalidurl'],
            'twitter': 'howtopizza',
            'github': 'frozenpizzacode',
        }
        res = self.app.put_json(
            url,
            payload,
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Invalid personal URL.')

    def test_serialize_social_editable(self):
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert_equal(res.json.get('twitter'), 'howtopizza')
        assert_equal(res.json.get('profileWebsites'), ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com'])
        assert_true(res.json.get('github') is None)
        assert_true(res.json['editable'])

    def test_serialize_social_not_editable(self):
        user2 = AuthUserFactory()
        self.user.social['twitter'] = 'howtopizza'
        self.user.social['profileWebsites'] = ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com']
        self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        )
        assert_equal(res.json.get('twitter'), 'howtopizza')
        assert_equal(res.json.get('profileWebsites'), ['http://www.cos.io', 'http://www.osf.io', 'http://www.wordup.com'])
        assert_true(res.json.get('github') is None)
        assert_false(res.json['editable'])

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
        assert_equal(
            res.json['addons']['github'],
            'abc'
        )

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
        assert_not_in('addons', res.json)

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
        self.app.put_json(url, payload, auth=self.user.auth)
        self.user.reload()
        assert_equal(len(self.user.jobs), 2)
        url = api_url_for('serialize_jobs')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(jobs):
            assert_equal(job, res.json['contents'][i])

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
        self.app.put_json(url, payload, auth=self.user.auth)
        self.user.reload()
        assert_equal(len(self.user.schools), 2)
        url = api_url_for('serialize_schools')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        for i, job in enumerate(schools):
            assert_equal(job, res.json['contents'][i])

    def test_unserialize_jobs(self):
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
        res = self.app.put_json(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.user.reload()
        # jobs field is updated
        assert_equal(self.user.jobs, jobs)

    def test_unserialize_names(self):
        fake_fullname_w_spaces = '    {}    '.format(fake.name())
        names = {
            'full': fake_fullname_w_spaces,
            'given': 'Tea',
            'middle': 'Gray',
            'family': 'Pot',
            'suffix': 'Ms.',
        }
        url = api_url_for('unserialize_names')
        res = self.app.put_json(url, names, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.user.reload()
        # user is updated
        assert_equal(self.user.fullname, fake_fullname_w_spaces.strip())
        assert_equal(self.user.given_name, names['given'])
        assert_equal(self.user.middle_names, names['middle'])
        assert_equal(self.user.family_name, names['family'])
        assert_equal(self.user.suffix, names['suffix'])

    def test_unserialize_schools(self):
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
        res = self.app.put_json(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.user.reload()
        # schools field is updated
        assert_equal(self.user.schools, schools)

    def test_unserialize_jobs_valid(self):
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
        res = self.app.put_json(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_update_user_timezone(self):
        assert_equal(self.user.timezone, 'Etc/UTC')
        payload = {'timezone': 'America/New_York', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put_json(url, payload, auth=self.user.auth)
        self.user.reload()
        assert_equal(self.user.timezone, 'America/New_York')

    def test_update_user_locale(self):
        assert_equal(self.user.locale, 'en_US')
        payload = {'locale': 'de_DE', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put_json(url, payload, auth=self.user.auth)
        self.user.reload()
        assert_equal(self.user.locale, 'de_DE')

    def test_update_user_locale_none(self):
        assert_equal(self.user.locale, 'en_US')
        payload = {'locale': None, 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put_json(url, payload, auth=self.user.auth)
        self.user.reload()
        assert_equal(self.user.locale, 'en_US')

    def test_update_user_locale_empty_string(self):
        assert_equal(self.user.locale, 'en_US')
        payload = {'locale': '', 'id': self.user._id}
        url = api_url_for('update_user', uid=self.user._id)
        self.app.put_json(url, payload, auth=self.user.auth)
        self.user.reload()
        assert_equal(self.user.locale, 'en_US')

    def test_cannot_update_user_without_user_id(self):
        user1 = AuthUserFactory()
        url = api_url_for('update_user')
        header = {'emails': [{'address': user1.username}]}
        res = self.app.put_json(url, header, auth=user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], '"id" is required')

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_add_emails_return_emails(self, send_mail):
        user1 = AuthUserFactory()
        url = api_url_for('update_user')
        email = 'test@cos.io'
        header = {'id': user1._id,
                  'emails': [{'address': user1.username, 'primary': True, 'confirmed': True},
                             {'address': email, 'primary': False, 'confirmed': False}
                  ]}
        res = self.app.put_json(url, header, auth=user1.auth)
        assert_equal(res.status_code, 200)
        assert_in('emails', res.json['profile'])
        assert_equal(len(res.json['profile']['emails']), 2)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_return_emails(self, send_mail):
        user1 = AuthUserFactory()
        url = api_url_for('resend_confirmation')
        email = 'test@cos.io'
        header = {'id': user1._id,
                  'email': {'address': email, 'primary': False, 'confirmed': False}
                  }
        res = self.app.put_json(url, header, auth=user1.auth)
        assert_equal(res.status_code, 200)
        assert_in('emails', res.json['profile'])
        assert_equal(len(res.json['profile']['emails']), 2)

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_update_user_mailing_lists(self, mock_get_mailchimp_api, send_mail):
        email = fake_email()
        self.user.emails.create(address=email)
        list_name = 'foo'
        self.user.mailchimp_mailing_lists[list_name] = True
        self.user.save()

        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)

        url = api_url_for('update_user', uid=self.user._id)
        emails = [
            {'address': self.user.username, 'primary': False, 'confirmed': True},
            {'address': email, 'primary': True, 'confirmed': True}]
        payload = {'locale': '', 'id': self.user._id, 'emails': emails}
        self.app.put_json(url, payload, auth=self.user.auth)

        assert mock_client.lists.unsubscribe.called
        mock_client.lists.unsubscribe.assert_called_with(
            id=list_id,
            email={'email': self.user.username},
            send_goodbye=True
        )
        mock_client.lists.subscribe.assert_called_with(
            id=list_id,
            email={'email': email},
            merge_vars={
                'fname': self.user.given_name,
                'lname': self.user.family_name,
            },
            double_optin=False,
            update_existing=True
        )
        handlers.celery_teardown_request()

    @mock.patch('framework.auth.views.mails.send_mail')
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_unsubscribe_mailchimp_not_called_if_user_not_subscribed(self, mock_get_mailchimp_api, send_mail):
        email = fake_email()
        self.user.emails.create(address=email)
        list_name = 'foo'
        self.user.mailchimp_mailing_lists[list_name] = False
        self.user.save()

        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}

        url = api_url_for('update_user', uid=self.user._id)
        emails = [
            {'address': self.user.username, 'primary': False, 'confirmed': True},
            {'address': email, 'primary': True, 'confirmed': True}]
        payload = {'locale': '', 'id': self.user._id, 'emails': emails}
        self.app.put_json(url, payload, auth=self.user.auth)

        assert_equal(mock_client.lists.unsubscribe.call_count, 0)
        assert_equal(mock_client.lists.subscribe.call_count, 0)
        handlers.celery_teardown_request()

    def test_user_with_quickfiles(self):
        quickfiles_node = QuickFilesNode.objects.get_for_user(self.user)
        create_test_file(quickfiles_node, self.user, filename='skrr_skrrrrrrr.pdf')

        url = web_url_for('profile_view_id', uid=self.user._id)
        res = self.app.get(url, auth=self.user.auth)

        assert_in('Quick files', res.body)

    def test_user_with_no_quickfiles(self):
        assert(not QuickFilesNode.objects.first().files.filter(type='osf.osfstoragefile').exists())

        url = web_url_for('profile_view_id', uid=self.user._primary_key)
        res = self.app.get(url, auth=self.user.auth)

        assert_not_in('Quick files', res.body)


class TestUserProfileApplicationsPage(OsfTestCase):

    def setUp(self):
        super(TestUserProfileApplicationsPage, self).setUp()
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()

        self.platform_app = ApiOAuth2ApplicationFactory(owner=self.user)
        self.detail_url = web_url_for('oauth_application_detail', client_id=self.platform_app.client_id)

    def test_non_owner_cant_access_detail_page(self):
        res = self.app.get(self.detail_url, auth=self.user2.auth, expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_owner_cant_access_deleted_application(self):
        self.platform_app.is_active = False
        self.platform_app.save()
        res = self.app.get(self.detail_url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.GONE)

    def test_owner_cant_access_nonexistent_application(self):
        url = web_url_for('oauth_application_detail', client_id='nonexistent')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.NOT_FOUND)

    def test_url_has_not_broken(self):
        assert_equal(self.platform_app.url, self.detail_url)


class TestUserProfileTokensPage(OsfTestCase):

    def setUp(self):
        super(TestUserProfileTokensPage, self).setUp()
        self.user = AuthUserFactory()
        self.token = ApiOAuth2PersonalTokenFactory()
        self.detail_url = web_url_for('personal_access_token_detail', _id=self.token._id)

    def test_url_has_not_broken(self):
        assert_equal(self.token.url, self.detail_url)


class TestUserAccount(OsfTestCase):

    def setUp(self):
        super(TestUserAccount, self).setUp()
        self.user = AuthUserFactory()
        self.user.set_password('password')
        self.user.auth = (self.user.username, 'password')
        self.user.save()

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_valid(self,
                                   mock_push_status_message,
                                   old_password='password',
                                   new_password='Pa$$w0rd',
                                   confirm_password='Pa$$w0rd'):
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': old_password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        res = self.app.post(url, post_data, auth=(self.user.username, old_password))
        assert_true(302, res.status_code)
        res = res.follow(auth=(self.user.username, new_password))
        assert_true(200, res.status_code)
        self.user.reload()
        assert_true(self.user.check_password(new_password))
        assert_true(mock_push_status_message.called)
        assert_in('Password updated successfully', mock_push_status_message.mock_calls[0][1][0])

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_invalid(self, mock_push_status_message, old_password='', new_password='',
                                     confirm_password='', error_message='Old password is invalid'):
        url = web_url_for('user_account_password')
        post_data = {
            'old_password': old_password,
            'new_password': new_password,
            'confirm_password': confirm_password,
        }
        res = self.app.post(url, post_data, auth=self.user.auth)
        assert_true(302, res.status_code)
        res = res.follow(auth=self.user.auth)
        assert_true(200, res.status_code)
        self.user.reload()
        assert_false(self.user.check_password(new_password))
        assert_true(mock_push_status_message.called)
        error_strings = [e[1][0] for e in mock_push_status_message.mock_calls]
        assert_in(error_message, error_strings)

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

    def test_password_change_invalid_blank_new_password(self):
        for password in ('', '      '):
            self.test_password_change_invalid_blank_password('password', password, 'new password')

    def test_password_change_invalid_blank_confirm_password(self):
        for password in ('', '      '):
            self.test_password_change_invalid_blank_password('password', 'new password', password)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_user_cannot_request_account_export_before_throttle_expires(self, send_mail):
        url = api_url_for('request_export')
        self.app.post(url, auth=self.user.auth)
        assert_true(send_mail.called)
        res = self.app.post(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(send_mail.call_count, 1)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_user_cannot_request_account_deactivation_before_throttle_expires(self, send_mail):
        url = api_url_for('request_deactivation')
        self.app.post(url, auth=self.user.auth)
        assert_true(send_mail.called)
        res = self.app.post(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(send_mail.call_count, 1)

    def test_get_unconfirmed_emails_exclude_external_identity(self):
        external_identity = {
            'service': {
                'AFI': 'LINK'
            }
        }
        self.user.add_unconfirmed_email("james@steward.com")
        self.user.add_unconfirmed_email("steward@james.com", external_identity=external_identity)
        self.user.save()
        unconfirmed_emails = self.user.get_unconfirmed_emails_exclude_external_identity()
        assert_in("james@steward.com", unconfirmed_emails)
        assert_not_in("steward@james.com", unconfirmed_emails)


class TestAddingContributorViews(OsfTestCase):

    def setUp(self):
        super(TestAddingContributorViews, self).setUp()
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator)
        self.auth = Auth(self.project.creator)
        # Authenticate all requests
        self.app.authenticate(*self.creator.auth)
        contributor_added.connect(notify_added_contributor)

    def test_serialize_unregistered_without_record(self):
        name, email = fake.name(), fake_email()
        res = serialize_unregistered(fullname=name, email=email)
        assert_equal(res['fullname'], name)
        assert_equal(res['email'], email)
        assert_equal(res['id'], None)
        assert_false(res['registered'])
        assert_true(res['profile_image_url'])
        assert_false(res['active'])

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
        contrib_data[0]['permission'] = 'admin'
        contrib_data[1]['permission'] = 'write'
        contrib_data[2]['permission'] = 'read'
        contrib_data[0]['visible'] = True
        contrib_data[1]['visible'] = True
        contrib_data[2]['visible'] = True
        res = deserialize_contributors(
            self.project,
            contrib_data,
            auth=Auth(self.creator))
        assert_equal(len(res), len(contrib_data))
        assert_true(res[0]['user'].is_registered)

        assert_false(res[1]['user'].is_registered)
        assert_true(res[1]['user']._id)

        assert_false(res[2]['user'].is_registered)
        assert_true(res[2]['user']._id)

    def test_deserialize_contributors_validates_fullname(self):
        name = "<img src=1 onerror=console.log(1)>"
        email = fake_email()
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [unreg_no_record]
        contrib_data[0]['permission'] = 'admin'
        contrib_data[0]['visible'] = True

        with assert_raises(ValidationError):
            deserialize_contributors(
                self.project,
                contrib_data,
                auth=Auth(self.creator),
                validate=True)

    def test_deserialize_contributors_validates_email(self):
        name = fake.name()
        email = "!@#$%%^&*"
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [unreg_no_record]
        contrib_data[0]['permission'] = 'admin'
        contrib_data[0]['visible'] = True

        with assert_raises(ValidationError):
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
        assert_false(res['active'])
        assert_false(res['registered'])
        assert_equal(res['id'], user._primary_key)
        assert_true(res['profile_image_url'])
        assert_equal(res['fullname'], name)
        assert_equal(res['email'], email)

    def test_add_contributor_with_unreg_contribs_and_reg_contribs(self):
        n_contributors_pre = len(self.project.contributors)
        reg_user = UserFactory()
        name, email = fake.name(), fake_email()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': email,
            'permission': 'admin',
            'visible': True,
        }
        reg_dict = add_contributor_json(reg_user)
        reg_dict['permission'] = 'admin'
        reg_dict['visible'] = True
        payload = {
            'users': [reg_dict, pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post_json(url, payload).maybe_follow()
        self.project.reload()
        assert_equal(len(self.project.contributors),
                     n_contributors_pre + len(payload['users']))

        new_unreg = auth.get_user(email=email)
        assert_false(new_unreg.is_registered)
        # unclaimed record was added
        new_unreg.reload()
        assert_in(self.project._primary_key, new_unreg.unclaimed_records)
        rec = new_unreg.get_unclaimed_record(self.project._primary_key)
        assert_equal(rec['name'], name)
        assert_equal(rec['email'], email)

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
            'permission': 'admin',
            'visible': True,
        }
        payload = {
            'users': [unreg_user],
            'node_ids': [comp1._primary_key, comp2._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert_true(self.project.can_edit(user=self.creator))
        self.app.post_json(url, payload, auth=self.creator.auth)

        # finalize_invitation should only have been called once
        assert_equal(mock_send_claim_email.call_count, 1)

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
            'permission': 'write',
            'visible': True}

        payload = {
            'users': [user_dict],
            'node_ids': [comp1._primary_key, comp2._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        self.app.post_json(url, payload, auth=self.creator.auth)

        # send_mail should only have been called once
        assert_equal(mock_send_mail.call_count, 1)

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
            'permission': 'write',
            'visible': True}

        payload = {
            'users': [user_dict],
            'node_ids': [sub_component._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        self.app.post_json(url, payload, auth=self.creator.auth)

        # send_mail is called for both the project and the sub-component
        assert_equal(mock_send_mail.call_count, 2)

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_email_sent_when_unreg_user_is_added(self, send_mail):
        name, email = fake.name(), fake_email()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': email,
            'permission': 'admin',
            'visible': True,
        }
        payload = {
            'users': [pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post_json(url, payload).maybe_follow()
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(email=email))

    @mock.patch('website.mails.send_mail')
    def test_email_sent_when_reg_user_is_added(self, send_mail):
        contributor = UserFactory()
        contributors = [{
            'user': contributor,
            'visible': True,
            'permissions': ['read', 'write']
        }]
        project = ProjectFactory(creator=self.auth.user)
        project.add_contributors(contributors, auth=self.auth)
        project.save()
        assert_true(send_mail.called)
        send_mail.assert_called_with(
            contributor.username,
            mails.CONTRIBUTOR_ADDED_DEFAULT,
            user=contributor,
            node=project,
            referrer_name=self.auth.user.fullname,
            all_global_subscriptions_none=False,
            branded_service=None,
            osf_contact_email=settings.OSF_CONTACT_EMAIL
        )
        assert_almost_equal(contributor.contributor_added_email_records[project._id]['last_sent'], int(time.time()), delta=1)

    @mock.patch('website.mails.send_mail')
    def test_contributor_added_email_sent_to_unreg_user(self, send_mail):
        unreg_user = UnregUserFactory()
        project = ProjectFactory()
        project.add_unregistered_contributor(fullname=unreg_user.fullname, email=unreg_user.email, auth=Auth(project.creator))
        project.save()
        assert_true(send_mail.called)

    @mock.patch('website.mails.send_mail')
    def test_forking_project_does_not_send_contributor_added_email(self, send_mail):
        project = ProjectFactory()
        project.fork_node(auth=Auth(project.creator))
        assert_false(send_mail.called)

    @mock.patch('website.mails.send_mail')
    def test_templating_project_does_not_send_contributor_added_email(self, send_mail):
        project = ProjectFactory()
        project.use_as_template(auth=Auth(project.creator))
        assert_false(send_mail.called)

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('website.mails.send_mail')
    def test_registering_project_does_not_send_contributor_added_email(self, send_mail, mock_archive):
        project = ProjectFactory()
        project.register_node(get_default_metaschema(), Auth(user=project.creator), '', None)
        assert_false(send_mail.called)

    @mock.patch('website.mails.send_mail')
    def test_notify_contributor_email_does_not_send_before_throttle_expires(self, send_mail):
        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        notify_added_contributor(project, contributor, auth)
        assert_true(send_mail.called)

        # 2nd call does not send email because throttle period has not expired
        notify_added_contributor(project, contributor, auth)
        assert_equal(send_mail.call_count, 1)

    @mock.patch('website.mails.send_mail')
    def test_notify_contributor_email_sends_after_throttle_expires(self, send_mail):
        throttle = 0.5

        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        notify_added_contributor(project, contributor, auth, throttle=throttle)
        assert_true(send_mail.called)

        time.sleep(1)  # throttle period expires
        notify_added_contributor(project, contributor, auth, throttle=throttle)
        assert_equal(send_mail.call_count, 2)

    @mock.patch('website.mails.send_mail')
    def test_add_contributor_to_fork_sends_email(self, send_mail):
        contributor = UserFactory()
        fork = self.project.fork_node(auth=Auth(self.creator))
        fork.add_contributor(contributor, auth=Auth(self.creator))
        fork.save()
        assert_true(send_mail.called)
        assert_equal(send_mail.call_count, 1)

    @mock.patch('website.mails.send_mail')
    def test_add_contributor_to_template_sends_email(self, send_mail):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        template.add_contributor(contributor, auth=Auth(self.creator))
        template.save()
        assert_true(send_mail.called)
        assert_equal(send_mail.call_count, 1)

    @mock.patch('website.mails.send_mail')
    def test_creating_fork_does_not_email_creator(self, send_mail):
        contributor = UserFactory()
        fork = self.project.fork_node(auth=Auth(self.creator))
        assert_false(send_mail.called)

    @mock.patch('website.mails.send_mail')
    def test_creating_template_does_not_email_creator(self, send_mail):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        assert_false(send_mail.called)

    def test_add_multiple_contributors_only_adds_one_log(self):
        n_logs_pre = self.project.logs.count()
        reg_user = UserFactory()
        name = fake.name()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': fake_email(),
            'permission': 'write',
            'visible': True,
        }
        reg_dict = add_contributor_json(reg_user)
        reg_dict['permission'] = 'admin'
        reg_dict['visible'] = True
        payload = {
            'users': [reg_dict, pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post_json(url, payload).maybe_follow()
        self.project.reload()
        assert_equal(self.project.logs.count(), n_logs_pre + 1)

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
            'permission': 'admin',
            'visible': True,
        }
        reg_dict = add_contributor_json(reg_user)
        reg_dict['permission'] = 'admin'
        reg_dict['visible'] = True
        payload = {
            'users': [reg_dict, pseudouser],
            'node_ids': [self.project._primary_key, child._primary_key]
        }
        url = '/api/v1/project/{0}/contributors/'.format(self.project._id)
        self.app.post_json(url, payload).maybe_follow()
        child.reload()
        assert_equal(child.contributors.count(),
                     n_contributors_pre + len(payload['users']))

    def tearDown(self):
        super(TestAddingContributorViews, self).tearDown()
        contributor_added.disconnect(notify_added_contributor)


class TestUserInviteViews(OsfTestCase):

    def setUp(self):
        super(TestUserInviteViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = '/api/v1/project/{0}/invite_contributor/'.format(
            self.project._primary_key)

    def test_invite_contributor_post_if_not_in_db(self):
        name, email = fake.name(), fake_email()
        res = self.app.post_json(
            self.invite_url,
            {'fullname': name, 'email': email},
            auth=self.user.auth,
        )
        contrib = res.json['contributor']
        assert_true(contrib['id'] is None)
        assert_equal(contrib['fullname'], name)
        assert_equal(contrib['email'], email)

    def test_invite_contributor_post_if_unreg_already_in_db(self):
        # A n unreg user is added to a different project
        name, email = fake.name(), fake_email()
        project2 = ProjectFactory()
        unreg_user = project2.add_unregistered_contributor(fullname=name, email=email,
                                                           auth=Auth(project2.creator))
        project2.save()
        res = self.app.post_json(self.invite_url,
                                 {'fullname': name, 'email': email}, auth=self.user.auth)
        expected = add_contributor_json(unreg_user)
        expected['fullname'] = name
        expected['email'] = email
        assert_equal(res.json['contributor'], expected)

    def test_invite_contributor_post_if_emaiL_already_registered(self):
        reg_user = UserFactory()
        # Tries to invite user that is already regiestered
        res = self.app.post_json(self.invite_url,
                                 {'fullname': fake.name(), 'email': reg_user.username},
                                 auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_invite_contributor_post_if_user_is_already_contributor(self):
        unreg_user = self.project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=Auth(self.project.creator)
        )
        self.project.save()
        # Tries to invite unreg user that is already a contributor
        res = self.app.post_json(self.invite_url,
                                 {'fullname': fake.name(), 'email': unreg_user.username},
                                 auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_invite_contributor_with_no_email(self):
        name = fake.name()
        res = self.app.post_json(self.invite_url,
                                 {'fullname': name, 'email': None}, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        data = res.json
        assert_equal(data['status'], 'success')
        assert_equal(data['contributor']['fullname'], name)
        assert_true(data['contributor']['email'] is None)
        assert_false(data['contributor']['registered'])

    def test_invite_contributor_requires_fullname(self):
        res = self.app.post_json(self.invite_url,
                                 {'email': 'brian@queen.com', 'fullname': ''}, auth=self.user.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

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

        assert_true(send_mail.called)
        assert_true(send_mail.called_with(
            to_addr=given_email,
            mail=mails.INVITE_DEFAULT
        ))

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

        assert_true(send_mail.called)
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
        with assert_raises(HTTPError):
            send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        assert_false(send_mail.called)


class TestClaimViews(OsfTestCase):

    def setUp(self):
        super(TestClaimViews, self).setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        self.given_name = fake.name()
        self.given_email = fake_email()
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
        assert_in(unregistered_user, self.project.contributors)

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for('claim_user_post', uid='undefined')
        self.app.post_json(invite_url, {
            'pk': unregistered_user._primary_key,
            'value': email
        })
        assert_equal(claim_email.call_count, 1)

        # set unregistered record email since we are mocking send_claim_email()
        unclaimed_record = unregistered_user.get_unclaimed_record(self.project._primary_key)
        unclaimed_record.update({'email': email})
        unregistered_user.save()

        # unregistered user then goes and makes an account with same email, before claiming themselves as contributor
        UserFactory(username=email, fullname=name)

        # claim link for the now registered email is accessed while not logged in
        token = unregistered_user.get_unclaimed_record(self.project._primary_key)['token']
        claim_url = '/user/{uid}/{pid}/claim/?token={token}'.format(
            uid=unregistered_user._id,
            pid=self.project._id,
            token=token
        )
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = '/user/{uid}/{pid}/claim/verify/{token}/'.format(
            uid=unregistered_user._id,
            pid=self.project._id,
            token=token
        )
        assert_equal(res.status_code, 302)
        assert_in(claim_registered_url, res.headers.get('Location'))

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
        assert_in(unregistered_user, self.project.contributors)

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for('claim_user_post', uid='undefined')
        self.app.post_json(invite_url, {
            'pk': unregistered_user._primary_key,
            'value': secondary_email
        })
        assert_equal(claim_email.call_count, 1)

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
        claim_url = '/user/{uid}/{pid}/claim/?token={token}'.format(
            uid=unregistered_user._id,
            pid=self.project._id,
            token=token
        )
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = '/user/{uid}/{pid}/claim/verify/{token}/'.format(
            uid=unregistered_user._id,
            pid=self.project._id,
            token=token
        )
        assert_equal(res.status_code, 302)
        assert_in(claim_registered_url, res.headers.get('Location'))

    def test_claim_user_invited_with_no_email_posts_to_claim_form(self):
        given_name = fake.name()
        invited_user = self.project.add_unregistered_contributor(
            fullname=given_name,
            email=None,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

        url = invited_user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, {
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        }, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_claim_user_post_with_registered_user_id(self, send_mail):
        # registered user who is attempting to claim the unclaimed contributor
        reg_user = UserFactory()
        payload = {
            # pk of unreg user record
            'pk': self.user._primary_key,
            'claimerId': reg_user._primary_key
        }
        url = '/api/v1/user/{uid}/{pid}/claim/email/'.format(
            uid=self.user._primary_key,
            pid=self.project._primary_key,
        )

        res = self.app.post_json(url, payload)

        # mail was sent
        assert_equal(send_mail.call_count, 2)
        # ... to the correct address
        referrer_call = send_mail.call_args_list[0]
        claimer_call = send_mail.call_args_list[1]
        args, _ = referrer_call
        assert_equal(args[0], self.referrer.username)
        args, _ = claimer_call
        assert_equal(args[0], reg_user.username)

        # view returns the correct JSON
        assert_equal(res.json, {
            'status': 'success',
            'email': reg_user.username,
            'fullname': self.given_name,
        })

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_registered_email(self, mock_send_mail):
        reg_user = UserFactory()
        send_claim_registered_email(
            claimer=reg_user,
            unclaimed_user=self.user,
            node=self.project
        )
        assert_equal(mock_send_mail.call_count, 2)
        first_call_args = mock_send_mail.call_args_list[0][0]
        assert_equal(first_call_args[0], self.referrer.username)
        second_call_args = mock_send_mail.call_args_list[1][0]
        assert_equal(second_call_args[0], reg_user.username)

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
        with assert_raises(HTTPError):
            send_claim_registered_email(
                claimer=reg_user,
                unclaimed_user=self.user,
                node=self.project,
            )
        assert_false(mock_send_mail.called)

    @mock.patch('website.project.views.contributor.send_claim_registered_email')
    def test_claim_user_post_with_email_already_registered_sends_correct_email(
            self, send_claim_registered_email):
        reg_user = UserFactory()
        payload = {
            'value': reg_user.username,
            'pk': self.user._primary_key
        }
        url = self.project.api_url_for('claim_user_post', uid=self.user._id)
        self.app.post_json(url, payload)
        assert_true(send_claim_registered_email.called)

    def test_user_with_removed_unclaimed_url_claiming(self):
        """ Tests that when an unclaimed user is removed from a project, the
        unregistered user object does not retain the token.
        """
        self.project.remove_contributor(self.user, Auth(user=self.referrer))

        assert_not_in(
            self.project._primary_key,
            self.user.unclaimed_records.keys()
        )

    def test_user_with_claim_url_cannot_claim_twice(self):
        """ Tests that when an unclaimed user is replaced on a project with a
        claimed user, the unregistered user object does not retain the token.
        """
        reg_user = AuthUserFactory()

        self.project.replace_contributor(self.user, reg_user)

        assert_not_in(
            self.project._primary_key,
            self.user.unclaimed_records.keys()
        )

    def test_claim_user_form_redirects_to_password_confirm_page_if_user_is_logged_in(self):
        reg_user = AuthUserFactory()
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=reg_user.auth)
        assert_equal(res.status_code, 302)
        res = res.follow(auth=reg_user.auth)
        token = self.user.get_unclaimed_record(self.project._primary_key)['token']
        expected = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token=token,
        )
        assert_equal(res.request.path, expected)

    def test_get_valid_form(self):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url).maybe_follow()
        assert_equal(res.status_code, 200)

    def test_invalid_claim_form_raise_400(self):
        uid = self.user._primary_key
        pid = self.project._primary_key
        url = '/user/{uid}/{pid}/claim/?token=badtoken'.format(**locals())
        res = self.app.get(url, expect_errors=True).maybe_follow()
        assert_equal(res.status_code, 400)

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_with_valid_data(self, mock_update_search_nodes):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, {
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert_equal(res.status_code, 302)
        location = res.headers.get('Location')
        assert_in('login?service=', location)
        assert_in('username', location)
        assert_in('verification_key', location)
        assert_in(self.project._primary_key, location)

        self.user.reload()
        assert_true(self.user.is_registered)
        assert_true(self.user.is_active)
        assert_not_in(self.project._primary_key, self.user.unclaimed_records)

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_removes_all_unclaimed_data(self, mock_update_search_nodes):
        # user has multiple unclaimed records
        p2 = ProjectFactory(creator=self.referrer)
        self.user.add_unclaimed_record(node=p2, referrer=self.referrer,
                                       given_name=fake.name())
        self.user.save()
        assert_true(len(self.user.unclaimed_records.keys()) > 1)  # sanity check
        url = self.user.get_claim_url(self.project._primary_key)
        self.app.post(url, {
            'username': self.given_email,
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        })
        self.user.reload()
        assert_equal(self.user.unclaimed_records, {})

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
        self.app.post(claim_url, {
            'username': unreg.username,
            'password': 'killerqueen', 'password2': 'killerqueen'
        })
        unreg.reload()
        # Full name was set correctly
        assert_equal(unreg.fullname, different_name)
        # CSL names were set correctly
        parsed_name = impute_names_model(different_name)
        assert_equal(unreg.given_name, parsed_name['given_name'])
        assert_equal(unreg.family_name, parsed_name['family_name'])

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_claim_user_post_returns_fullname(self, send_mail):
        url = '/api/v1/user/{0}/{1}/claim/email/'.format(self.user._primary_key,
                                                         self.project._primary_key)
        res = self.app.post_json(url,
                                 {'value': self.given_email,
                                     'pk': self.user._primary_key},
                                 auth=self.referrer.auth)
        assert_equal(res.json['fullname'], self.given_name)
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(to_addr=self.given_email))

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_claim_user_post_if_email_is_different_from_given_email(self, send_mail):
        email = fake_email()  # email that is different from the one the referrer gave
        url = '/api/v1/user/{0}/{1}/claim/email/'.format(self.user._primary_key,
                                                         self.project._primary_key)
        self.app.post_json(url,
                           {'value': email, 'pk': self.user._primary_key}
                           )
        assert_true(send_mail.called)
        assert_equal(send_mail.call_count, 2)
        call_to_invited = send_mail.mock_calls[0]
        assert_true(call_to_invited.called_with(
            to_addr=email
        ))
        call_to_referrer = send_mail.mock_calls[1]
        assert_true(call_to_referrer.called_with(
            to_addr=self.given_email
        ))

    def test_claim_url_with_bad_token_returns_400(self):
        url = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token='badtoken',
        )
        res = self.app.get(url, auth=self.referrer.auth, expect_errors=400)
        assert_equal(res.status_code, 400)

    def test_cannot_claim_user_with_user_who_is_already_contributor(self):
        # user who is already a contirbutor to the project
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        # Claiming user goes to claim url, but contrib is already logged in
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(
            url,
            auth=contrib.auth,
        ).follow(
            auth=contrib.auth,
            expect_errors=True,
        )
        # Response is a 400
        assert_equal(res.status_code, 400)


class TestPointerViews(OsfTestCase):

    def setUp(self):
        super(TestPointerViews, self).setUp()
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

        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, 200)

        has_controls = res.lxml.xpath('//li[@node_id]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
        assert_true(has_controls)

    def test_pointer_list_write_contributor_can_remove_public_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)

        for i in xrange(3):
            self.project.add_pointer(ProjectFactory(creator=self.user),
                                     auth=Auth(user=self.user))
        self.project.save()

        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, 200)

        has_controls = res.lxml.xpath(
            '//li[@node_id]//i[contains(@class, "remove-pointer")]')
        assert_equal(len(has_controls), 3)

    def test_pointer_list_read_contributor_cannot_remove_private_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)
        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=[permissions.READ])

        self._make_pointer_only_user_can_see(user2, self.project)
        self.project.save()

        res = self.app.get(url, auth=user2.auth).maybe_follow()
        assert_equal(res.status_code, 200)

        pointer_nodes = res.lxml.xpath('//li[@node_id]')
        has_controls = res.lxml.xpath('//li[@node_id]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
        assert_equal(len(pointer_nodes), 1)
        assert_false(has_controls)

    def test_pointer_list_read_contributor_cannot_remove_public_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)

        self.project.add_pointer(ProjectFactory(creator=self.user,
                                                is_public=True),
                                 auth=Auth(user=self.user))

        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=[permissions.READ])
        self.project.save()

        res = self.app.get(url, auth=user2.auth).maybe_follow()
        assert_equal(res.status_code, 200)

        pointer_nodes = res.lxml.xpath('//li[@node_id]')
        has_controls = res.lxml.xpath(
            '//li[@node_id]//i[contains(@class, "remove-pointer")]')
        assert_equal(len(pointer_nodes), 1)
        assert_equal(len(has_controls), 0)

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
        assert_equal(res.status_code, 200)
        # pointer_project's id is included in response, but folder's id is not
        pointer_ids = [each['id'] for each in res.json['pointed']]
        assert_in(pointer_project._id, pointer_ids)
        assert_not_in(collection._id, pointer_ids)

    def test_add_pointers(self):

        url = self.project.api_url + 'pointer/'
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        self.app.post_json(
            url,
            {'nodeIds': node_ids},
            auth=self.user.auth,
        ).maybe_follow()

        self.project.reload()
        assert_equal(
            self.project.nodes_active.count(),
            5
        )

    def test_add_the_same_pointer_more_than_once(self):
        url = self.project.api_url + 'pointer/'
        double_node = NodeFactory()

        self.app.post_json(
            url,
            {'nodeIds': [double_node._id]},
            auth=self.user.auth,
        )
        res = self.app.post_json(
            url,
            {'nodeIds': [double_node._id]},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_add_pointers_no_user_logg_in(self):

        url = self.project.api_url_for('add_pointers')
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        res = self.app.post_json(
            url,
            {'nodeIds': node_ids},
            auth=None,
            expect_errors=True
        )

        assert_equal(res.status_code, 401)

    def test_add_pointers_public_non_contributor(self):

        project2 = ProjectFactory()
        project2.set_privacy('public')
        project2.save()

        url = self.project.api_url_for('add_pointers')

        self.app.post_json(
            url,
            {'nodeIds': [project2._id]},
            auth=self.user.auth,
        ).maybe_follow()

        self.project.reload()
        assert_equal(
            self.project.nodes_active.count(),
            1
        )

    def test_add_pointers_contributor(self):
        user2 = AuthUserFactory()
        self.project.add_contributor(user2)
        self.project.save()

        url = self.project.api_url_for('add_pointers')
        node_ids = [
            NodeFactory()._id
            for _ in range(5)
        ]
        self.app.post_json(
            url,
            {'nodeIds': node_ids},
            auth=user2.auth,
        ).maybe_follow()

        self.project.reload()
        assert_equal(
            self.project.linked_nodes.count(),
            5
        )

    def test_add_pointers_not_provided(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)


    def test_remove_pointer(self):
        url = self.project.api_url + 'pointer/'
        node = NodeFactory()
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)
        self.app.delete_json(
            url,
            {'pointerId': pointer.node._id},
            auth=self.user.auth,
        )
        self.project.reload()
        assert_equal(
            len(list(self.project.nodes)),
            0
        )

    def test_remove_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_remove_pointer_not_found(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete_json(
            url,
            {'pointerId': None},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_remove_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.delete_json(
            url,
            {'pointerId': 'somefakeid'},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_forking_pointer_works(self):
        url = self.project.api_url + 'pointer/fork/'
        linked_node = NodeFactory(creator=self.user)
        pointer = self.project.add_pointer(linked_node, auth=self.consolidate_auth)
        assert_true(linked_node.id, pointer.child.id)
        res = self.app.post_json(url, {'nodeId': pointer.child._id}, auth=self.user.auth)
        assert_equal(res.status_code, 201)
        assert_in('node', res.json['data'])
        fork = res.json['data']['node']
        assert_equal(fork['title'], 'Fork of {}'.format(linked_node.title))

    def test_fork_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post_json(url, {}, auth=self.user.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_fork_pointer_not_found(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post_json(
            url,
            {'nodeId': None},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_fork_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post_json(
            url,
            {'nodeId': 'somefakeid'},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_before_register_with_pointer(self):
        # Assert that link warning appears in before register callback.
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert_equal(len(prompts), 1)

    def test_before_fork_with_pointer(self):
        """Assert that link warning appears in before fork callback."""
        node = NodeFactory()
        self.project.add_pointer(node, auth=self.consolidate_auth)
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your registration' in prompt
        ]
        assert_equal(len(prompts), 1)

    def test_before_register_no_pointer(self):
        """Assert that link warning does not appear in before register callback."""
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert_equal(len(prompts), 0)

    def test_before_fork_no_pointer(self):
        """Assert that link warning does not appear in before fork callback."""
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your registration' in prompt
        ]
        assert_equal(len(prompts), 0)

    def test_get_pointed(self):
        pointing_node = ProjectFactory(creator=self.user)
        pointing_node.add_pointer(self.project, auth=Auth(self.user))
        url = self.project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        pointed = res.json['pointed']
        assert_equal(len(pointed), 1)
        assert_equal(pointed[0]['url'], pointing_node.url)
        assert_equal(pointed[0]['title'], pointing_node.title)
        assert_equal(pointed[0]['authorShort'], abbrev_authors(pointing_node))

    def test_get_pointed_private(self):
        secret_user = UserFactory()
        pointing_node = ProjectFactory(creator=secret_user)
        pointing_node.add_pointer(self.project, auth=Auth(secret_user))
        url = self.project.api_url_for('get_pointed')
        res = self.app.get(url, auth=self.user.auth)
        pointed = res.json['pointed']
        assert_equal(len(pointed), 1)
        assert_equal(pointed[0]['url'], None)
        assert_equal(pointed[0]['title'], 'Private Component')
        assert_equal(pointed[0]['authorShort'], 'Private Author(s)')

    def test_can_template_project_linked_to_each_other(self):
        project2 = ProjectFactory(creator=self.user)
        self.project.add_pointer(project2, auth=Auth(user=self.user))
        project2.add_pointer(self.project, auth=Auth(user=self.user))
        template = self.project.use_as_template(auth=Auth(user=self.user))

        assert_true(template)
        assert_equal(template.title, 'Templated from ' + self.project.title)
        assert_not_in(project2, template.linked_nodes)


class TestPublicViews(OsfTestCase):

    def test_explore(self):
        res = self.app.get("/explore/").maybe_follow()
        assert_equal(res.status_code, 200)


class TestAuthViews(OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_ok(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post_json(
            url,
            {
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
            }
        )
        user = OSFUser.objects.get(username=email)
        assert_equal(user.fullname, name)

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2902
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_email_case_insensitive(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        self.app.post_json(
            url,
            {
                'fullName': name,
                'email1': email,
                'email2': str(email).upper(),
                'password': password,
            }
        )
        user = OSFUser.objects.get(username=email)
        assert_equal(user.fullname, name)

    @mock.patch('framework.auth.views.send_confirm_email')
    def test_register_scrubs_username(self, _):
        url = api_url_for('register_user')
        name = "<i>Eunice</i> O' \"Cornwallis\"<script type='text/javascript' src='http://www.cornify.com/js/cornify.js'></script><script type='text/javascript'>cornify_add()</script>"
        email, password = fake_email(), 'underpressure'
        res = self.app.post_json(
            url,
            {
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
            }
        )

        expected_scrub_username = "Eunice O' \"Cornwallis\"cornify_add()"
        user = OSFUser.objects.get(username=email)

        assert_equal(res.status_code, http.OK)
        assert_equal(user.fullname, expected_scrub_username)

    def test_register_email_mismatch(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        res = self.app.post_json(
            url,
            {
                'fullName': name,
                'email1': email,
                'email2': email + 'lol',
                'password': password,
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        users = OSFUser.objects.filter(username=email)
        assert_equal(users.count(), 0)

    def test_register_blacklisted_email_domain(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), 'bad@mailinator.com', 'agreatpasswordobviously'
        res = self.app.post_json(
            url, {
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password
            },
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        users = OSFUser.objects.filter(username=email)
        assert_equal(users.count(), 0)

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=True)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_good_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        captcha = 'some valid captcha'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post_json(
                url,
                {
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    'g-recaptcha-response': captcha,
                }
            )
            validate_recaptcha.assert_called_with(captcha, remote_ip=None)
            assert_equal(resp.status_code, http.OK)
            user = OSFUser.objects.get(username=email)
            assert_equal(user.fullname, name)

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=False)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_missing_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post_json(
                url,
                {
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    # 'g-recaptcha-response': 'supposed to be None',
                },
                expect_errors=True
            )
            validate_recaptcha.assert_called_with(None, remote_ip=None)
            assert_equal(resp.status_code, http.BAD_REQUEST)

    @mock.patch('framework.auth.views.validate_recaptcha', return_value=False)
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_bad_captcha(self, _, validate_recaptcha):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with mock.patch.object(settings, 'RECAPTCHA_SITE_KEY', 'some_value'):
            resp = self.app.post_json(
                url,
                {
                    'fullName': name,
                    'email1': email,
                    'email2': str(email).upper(),
                    'password': password,
                    'g-recaptcha-response': 'bad captcha',
                },
                expect_errors=True
            )
            assert_equal(resp.status_code, http.BAD_REQUEST)

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
        self.app.post_json(url, payload)

        new_user.reload()

        # New user confirms by following confirmation link
        confirm_url = new_user.get_confirmation_url(email, external=False)
        self.app.get(confirm_url)

        new_user.reload()
        # Password and fullname should be updated
        assert_true(new_user.is_confirmed)
        assert_true(new_user.check_password(password))
        assert_equal(new_user.fullname, real_name)

    @mock.patch('framework.auth.views.send_confirm_email')
    def test_register_sends_user_registered_signal(self, mock_send_confirm_email):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake_email(), 'underpressure'
        with capture_signals() as mock_signals:
            self.app.post_json(
                url,
                {
                    'fullName': name,
                    'email1': email,
                    'email2': email,
                    'password': password,
                }
            )
        assert_equal(mock_signals.signals_sent(), set([auth.signals.user_registered,
                                                       auth.signals.unconfirmed_user_created]))
        assert_true(mock_send_confirm_email.called)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation(self, send_mail):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        self.app.put_json(url, {'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(
            to_addr=email
        ))
        self.user.reload()
        assert_not_equal(token, self.user.get_confirmation_token(email))
        with assert_raises(InvalidTokenError):
            self.user.get_unconfirmed_email_for_token(token)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_click_confirmation_email(self, send_mail):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token, self.user.username)
        res = self.app.get(url)
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], True)
        assert_equal(res.status_code, 302)
        login_url = 'login?service'
        assert_in(login_url, res.body)

    def test_get_email_to_add_no_email(self):
        email_verifications = self.user.unconfirmed_email_info
        assert_equal(email_verifications, [])

    def test_get_unconfirmed_email(self):
        email = 'test@mail.com'
        self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        assert_equal(email_verifications, [])

    def test_get_email_to_add(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token, self.user.username)
        self.app.get(url)
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], True)
        email_verifications = self.user.unconfirmed_email_info
        assert_equal(email_verifications[0]['address'], 'test@mail.com')

    def test_add_email(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token)
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put_json(put_email_url, email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert_equal(res.json_body['status'], 'success')
        assert_equal(self.user.emails.last().address, 'test@mail.com')

    def test_remove_email(self):
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token)
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        remove_email_url = api_url_for('unconfirmed_email_remove')
        remove_res = self.app.delete_json(remove_email_url, email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert_equal(remove_res.json_body['status'], 'success')
        assert_equal(self.user.unconfirmed_email_info, [])

    def test_add_expired_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = 'test@mail.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.email_verifications[token]['expiration'] = timezone.now() - dt.timedelta(days=100)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['email'], email)
        self.user.clean_email_verifications(given_token=token)
        unconfirmed_emails = self.user.unconfirmed_email_info
        assert_equal(unconfirmed_emails, [])
        assert_equal(self.user.email_verifications, {})

    def test_clean_email_verifications(self):
        # Do not return bad token and removes it from user.email_verifications
        email = 'test@mail.com'
        token = 'blahblahblah'
        self.user.email_verifications[token] = {'expiration': timezone.now() + dt.timedelta(days=1),
                                                'email': email,
                                                'confirmed': False }
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['email'], email)
        self.user.clean_email_verifications(given_token=token)
        unconfirmed_emails = self.user.unconfirmed_email_info
        assert_equal(unconfirmed_emails, [])
        assert_equal(self.user.email_verifications, {})

    def test_clean_email_verifications_when_email_verifications_is_an_empty_dict(self):
        self.user.email_verifications = {}
        self.user.save()
        ret = self.user.clean_email_verifications()
        assert_equal(ret, None)
        assert_equal(self.user.email_verifications, {})

    def test_add_invalid_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = u'\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello@yourmom.com'
        # illegal_str = u'\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello'
        # illegal_str += unichr(0xd800) + unichr(0xdbff) + ' World'
        # email = 'test@mail.com'
        with assert_raises(ValidationError):
            self.user.add_unconfirmed_email(email)

    def test_add_email_merge(self):
        email = "copy@cat.com"
        dupe = UserFactory(
            username=email,
        )
        dupe.save()
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token)
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.unconfirmed_email_info
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put_json(put_email_url, email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert_equal(res.json_body['status'], 'success')
        assert_equal(self.user.emails.last().address, 'copy@cat.com')

    def test_resend_confirmation_without_user_id(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        res = self.app.put_json(url, {'email': header}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], '"id" is required')

    def test_resend_confirmation_without_email(self):
        url = api_url_for('resend_confirmation')
        res = self.app.put_json(url, {'id': self.user._id}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_resend_confirmation_not_work_for_primary_email(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': True, 'confirmed': False}
        res = self.app.put_json(url, {'id': self.user._id, 'email': header}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Cannnot resend confirmation for confirmed emails')

    def test_resend_confirmation_not_work_for_confirmed_email(self):
        email = 'test@mail.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': True}
        res = self.app.put_json(url, {'id': self.user._id, 'email': header}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Cannnot resend confirmation for confirmed emails')

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_does_not_send_before_throttle_expires(self, send_mail):
        email = 'test@mail.com'
        self.user.save()
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': False}
        self.app.put_json(url, {'id': self.user._id, 'email': header}, auth=self.user.auth)
        assert_true(send_mail.called)
        # 2nd call does not send email because throttle period has not expired
        res = self.app.put_json(url, {'id': self.user._id, 'email': header}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_confirm_email_clears_unclaimed_records_and_revokes_token(self):
        unclaimed_user = UnconfirmedUserFactory()
        # unclaimed user has been invited to a project.
        referrer = UserFactory()
        project = ProjectFactory(creator=referrer)
        unclaimed_user.add_unclaimed_record(project, referrer, 'foo')
        unclaimed_user.save()

        # sanity check
        assert_equal(len(unclaimed_user.email_verifications.keys()), 1)

        # user goes to email confirmation link
        token = unclaimed_user.get_confirmation_token(unclaimed_user.username)
        url = web_url_for('confirm_email_get', uid=unclaimed_user._id, token=token)
        res = self.app.get(url)
        assert_equal(res.status_code, 302)

        # unclaimed records and token are cleared
        unclaimed_user.reload()
        assert_equal(unclaimed_user.unclaimed_records, {})
        assert_equal(len(unclaimed_user.email_verifications.keys()), 0)

    def test_confirmation_link_registers_user(self):
        user = OSFUser.create_unconfirmed('brian@queen.com', 'bicycle123', 'Brian May')
        assert_false(user.is_registered)  # sanity check
        user.save()
        confirmation_url = user.get_confirmation_url('brian@queen.com', external=False)
        res = self.app.get(confirmation_url)
        assert_equal(res.status_code, 302, 'redirects to settings page')
        res = res.follow()
        user.reload()
        assert_true(user.is_registered)


class TestAuthLoginAndRegisterLogic(OsfTestCase):

    def setUp(self):
        super(TestAuthLoginAndRegisterLogic, self).setUp()
        self.no_auth = Auth()
        self.user_auth = AuthUserFactory()
        self.auth = Auth(user=self.user_auth)
        self.next_url = web_url_for('my_projects', _absolute=True)
        self.invalid_campaign = 'invalid_campaign'

    def test_osf_login_with_auth(self):
        # login: user with auth
        data = login_and_register_handler(self.auth)
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), web_url_for('dashboard', _absolute=True))

    def test_osf_login_without_auth(self):
        # login: user without auth
        data = login_and_register_handler(self.no_auth)
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), web_url_for('dashboard', _absolute=True))

    def test_osf_register_with_auth(self):
        # register: user with auth
        data = login_and_register_handler(self.auth, login=False)
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), web_url_for('dashboard', _absolute=True))

    def test_osf_register_without_auth(self):
        # register: user without auth
        data = login_and_register_handler(self.no_auth, login=False)
        assert_equal(data.get('status_code'), http.OK)
        assert_equal(data.get('next_url'), web_url_for('dashboard', _absolute=True))

    def test_next_url_login_with_auth(self):
        # next_url login: user with auth
        data = login_and_register_handler(self.auth, next_url=self.next_url)
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), self.next_url)

    def test_next_url_login_without_auth(self):
        # login: user without auth
        request.url = web_url_for('auth_login', next=self.next_url, _absolute=True)
        data = login_and_register_handler(self.no_auth, next_url=self.next_url)
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), get_login_url(request.url))

    def test_next_url_register_with_auth(self):
        # register: user with auth
        data = login_and_register_handler(self.auth, login=False, next_url=self.next_url)
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), self.next_url)

    def test_next_url_register_without_auth(self):
        # register: user without auth
        data = login_and_register_handler(self.no_auth, login=False, next_url=self.next_url)
        assert_equal(data.get('status_code'), http.OK)
        assert_equal(data.get('next_url'), request.url)

    def test_institution_login_and_register(self):
        pass

    def test_institution_login_with_auth(self):
        # institution login: user with auth
        data = login_and_register_handler(self.auth, campaign='institution')
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), web_url_for('dashboard', _absolute=True))

    def test_institution_login_without_auth(self):
        # institution login: user without auth
        data = login_and_register_handler(self.no_auth, campaign='institution')
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(
            data.get('next_url'),
            get_login_url(web_url_for('dashboard', _absolute=True), campaign='institution'))

    def test_institution_login_next_url_with_auth(self):
        # institution login: user with auth and next url
        data = login_and_register_handler(self.auth, next_url=self.next_url, campaign='institution')
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), self.next_url)

    def test_institution_login_next_url_without_auth(self):
        # institution login: user without auth and next url
        data = login_and_register_handler(self.no_auth, next_url=self.next_url ,campaign='institution')
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(
            data.get('next_url'),
            get_login_url(self.next_url, campaign='institution'))

    def test_institution_regsiter_with_auth(self):
        # institution register: user with auth
        data = login_and_register_handler(self.auth, login=False, campaign='institution')
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(data.get('next_url'), web_url_for('dashboard', _absolute=True))

    def test_institution_register_without_auth(self):
        # institution register: user without auth
        data = login_and_register_handler(self.no_auth, login=False, campaign='institution')
        assert_equal(data.get('status_code'), http.FOUND)
        assert_equal(
            data.get('next_url'),
            get_login_url(web_url_for('dashboard', _absolute=True), campaign='institution')
        )

    def test_campaign_login_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user with auth
            data = login_and_register_handler(self.auth, campaign=campaign)
            assert_equal(data.get('status_code'), http.FOUND)
            assert_equal(data.get('next_url'), campaign_url_for(campaign))

    def test_campaign_login_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user without auth
            data = login_and_register_handler(self.no_auth, campaign=campaign)
            assert_equal(data.get('status_code'), http.FOUND)
            assert_equal(
                data.get('next_url'),
                web_url_for('auth_register', campaign=campaign, next=campaign_url_for(campaign))
            )

    def test_campaign_register_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user with auth
            data = login_and_register_handler(self.auth, login=False, campaign=campaign)
            assert_equal(data.get('status_code'), http.FOUND)
            assert_equal(data.get('next_url'), campaign_url_for(campaign))

    def test_campaign_register_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user without auth
            data = login_and_register_handler(self.no_auth, login=False, campaign=campaign)
            assert_equal(data.get('status_code'), http.OK)
            if is_native_login(campaign):
                # native campaign: prereg and erpc
                assert_equal(data.get('next_url'), campaign_url_for(campaign))
            elif is_proxy_login(campaign):
                # proxy campaign: preprints and branded ones
                assert_equal(
                    data.get('next_url'),
                    web_url_for('auth_login', next=campaign_url_for(campaign), _absolute=True)
                )

    def test_campaign_next_url_login_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user with auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.auth, campaign=campaign, next_url=next_url)
            assert_equal(data.get('status_code'), http.FOUND)
            assert_equal(data.get('next_url'), next_url)

    def test_campaign_next_url_login_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign login: user without auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.no_auth, campaign=campaign, next_url=next_url)
            assert_equal(data.get('status_code'), http.FOUND)
            assert_equal(
                data.get('next_url'),
                web_url_for('auth_register', campaign=campaign, next=next_url)
            )

    def test_campaign_next_url_register_with_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user with auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.auth, login=False, campaign=campaign, next_url=next_url)
            assert_equal(data.get('status_code'), http.FOUND)
            assert_equal(data.get('next_url'), next_url)

    def test_campaign_next_url_register_without_auth(self):
        for campaign in get_campaigns():
            if is_institution_login(campaign):
                continue
            # campaign register: user without auth
            next_url = campaign_url_for(campaign)
            data = login_and_register_handler(self.no_auth, login=False, campaign=campaign, next_url=next_url)
            assert_equal(data.get('status_code'), http.OK)
            if is_native_login(campaign):
                # native campaign: prereg and erpc
                assert_equal(data.get('next_url'), next_url)
            elif is_proxy_login(campaign):
                # proxy campaign: preprints and branded ones
                assert_equal(
                    data.get('next_url'),
                    web_url_for('auth_login', next= next_url, _absolute=True)
                )

    def test_invalid_campaign_login_without_auth(self):
        data = login_and_register_handler(
            self.no_auth,
            login=True,
            campaign=self.invalid_campaign,
            next_url=self.next_url
        )
        redirect_url = web_url_for('auth_login', campaigns=None, next=self.next_url)
        assert_equal(data['status_code'], http.FOUND)
        assert_equal(data['next_url'], redirect_url)
        assert_equal(data['campaign'], None)

    def test_invalid_campaign_register_without_auth(self):
        data = login_and_register_handler(
            self.no_auth,
            login=False,
            campaign=self.invalid_campaign,
            next_url=self.next_url
        )
        redirect_url = web_url_for('auth_register', campaigns=None, next=self.next_url)
        assert_equal(data['status_code'], http.FOUND)
        assert_equal(data['next_url'], redirect_url)
        assert_equal(data['campaign'], None)

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
        assert_equal(data.get('status_code'), 'auth_logout')
        assert_equal(data.get('next_url'), self.next_url)

    def test_register_logout_flage_without(self):
        # the second step is to land user on register page with "MUST LOGIN" warning
        data = login_and_register_handler(self.no_auth, login=False, campaign=None, next_url=self.next_url, logout=True)
        assert_equal(data.get('status_code'), http.OK)
        assert_equal(data.get('next_url'), self.next_url)
        assert_true(data.get('must_login_warning'))


class TestAuthLogout(OsfTestCase):

    def setUp(self):
        super(TestAuthLogout, self).setUp()
        self.goodbye_url = web_url_for('goodbye', _absolute=True)
        self.redirect_url = web_url_for('forgot_password_get', _absolute=True)
        self.valid_next_url = web_url_for('dashboard', _absolute=True)
        self.invalid_next_url = 'http://localhost:1234/abcde'
        self.auth_user = AuthUserFactory()

    def tearDown(self):
        super(TestAuthLogout, self).tearDown()
        OSFUser.objects.all().delete()
        assert_equal(OSFUser.objects.count(), 0)

    def test_logout_with_valid_next_url_logged_in(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.valid_next_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(cas.get_logout_url(logout_url), resp.headers['Location'])

    def test_logout_with_valid_next_url_logged_out(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.valid_next_url)
        resp = self.app.get(logout_url, auth=None)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(self.valid_next_url, resp.headers['Location'])

    def test_logout_with_invalid_next_url_logged_in(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.invalid_next_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(cas.get_logout_url(self.goodbye_url), resp.headers['Location'])

    def test_logout_with_invalid_next_url_logged_out(self):
        logout_url = web_url_for('auth_logout', _absolute=True, next=self.invalid_next_url)
        resp = self.app.get(logout_url, auth=None)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(cas.get_logout_url(self.goodbye_url), resp.headers['Location'])

    def test_logout_with_redirect_url(self):
        logout_url = web_url_for('auth_logout', _absolute=True, redirect_url=self.redirect_url)
        resp = self.app.get(logout_url, auth=self.auth_user.auth)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(cas.get_logout_url(self.redirect_url), resp.headers['Location'])

    def test_logout_with_no_parameter(self):
        logout_url = web_url_for('auth_logout', _absolute=True)
        resp = self.app.get(logout_url, auth=None)
        assert_equal(resp.status_code, http.FOUND)
        assert_equal(cas.get_logout_url(self.goodbye_url), resp.headers['Location'])


class TestExternalAuthViews(OsfTestCase):

    def setUp(self):
        super(TestExternalAuthViews, self).setUp()
        name, email = fake.name(), fake_email()
        self.provider_id = fake.ean()
        external_identity = {
            'orcid': {
                self.provider_id: 'CREATE'
            }
        }
        self.user = OSFUser.create_unconfirmed(
            username=email,
            password=str(fake.password()),
            fullname=name,
            external_identity=external_identity,
        )
        self.user.save()
        self.auth = Auth(self.user)

    def test_external_login_email_get_with_invalid_session(self):
        url = web_url_for('external_login_email_get')
        resp = self.app.get(url, expect_errors=True)
        assert_equal(resp.status_code, 401)

    def test_external_login_confirm_email_get_with_another_user_logged_in(self):
        another_user = AuthUserFactory()
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url, auth=another_user.auth)
        assert_equal(res.status_code, 302, 'redirects to cas logout')
        assert_in('/logout?service=', res.location)
        assert_in(url, res.location)

    def test_external_login_confirm_email_get_without_destination(self):
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid')
        res = self.app.get(url, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 400, 'bad request')

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_create(self, mock_welcome):
        assert_false(self.user.is_registered)
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url, auth=self.auth)
        assert_equal(res.status_code, 302, 'redirects to cas login')
        assert_in('/login?service=', res.location)
        assert_in('new=true', res.location)

        assert_equal(mock_welcome.call_count, 1)

        self.user.reload()
        assert_equal(self.user.external_identity['orcid'][self.provider_id], 'VERIFIED')
        assert_true(self.user.is_registered)
        assert_true(self.user.has_usable_password())

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_link(self, mock_link_confirm):
        self.user.external_identity['orcid'][self.provider_id] = 'LINK'
        self.user.save()
        assert_false(self.user.is_registered)
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url, auth=self.auth)
        assert_equal(res.status_code, 302, 'redirects to cas login')
        assert_in('/login?service=', res.location)
        assert_not_in('new=true', res.location)

        assert_equal(mock_link_confirm.call_count, 1)

        self.user.reload()
        assert_equal(self.user.external_identity['orcid'][self.provider_id], 'VERIFIED')
        assert_true(self.user.is_registered)
        assert_true(self.user.has_usable_password())

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_duped_id(self, mock_confirm):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert_equal(dupe_user.external_identity, self.user.external_identity)
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url, auth=self.auth)
        assert_equal(res.status_code, 302, 'redirects to cas login')
        assert_in('/login?service=', res.location)

        assert_equal(mock_confirm.call_count, 1)

        self.user.reload()
        dupe_user.reload()

        assert_equal(self.user.external_identity['orcid'][self.provider_id], 'VERIFIED')
        assert_equal(dupe_user.external_identity, {})

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_duping_id(self, mock_confirm):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'VERIFIED'}})
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, 403, 'only allows one user to link an id')

        assert_equal(mock_confirm.call_count, 0)

        self.user.reload()
        dupe_user.reload()

        assert_equal(dupe_user.external_identity['orcid'][self.provider_id], 'VERIFIED')
        assert_equal(self.user.external_identity, {})

    def test_ensure_external_identity_uniqueness_unverified(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert_equal(dupe_user.external_identity, self.user.external_identity)

        ensure_external_identity_uniqueness('orcid', self.provider_id, self.user)

        dupe_user.reload()
        self.user.reload()

        assert_equal(dupe_user.external_identity, {})
        assert_equal(self.user.external_identity, {'orcid': {self.provider_id: 'CREATE'}})

    def test_ensure_external_identity_uniqueness_verified(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'VERIFIED'}})
        assert_equal(dupe_user.external_identity, {'orcid': {self.provider_id: 'VERIFIED'}})
        assert_not_equal(dupe_user.external_identity, self.user.external_identity)

        with assert_raises(ValidationError):
            ensure_external_identity_uniqueness('orcid', self.provider_id, self.user)

        dupe_user.reload()
        self.user.reload()

        assert_equal(dupe_user.external_identity, {'orcid': {self.provider_id: 'VERIFIED'}})
        assert_equal(self.user.external_identity, {})

    def test_ensure_external_identity_uniqueness_multiple(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert_equal(dupe_user.external_identity, self.user.external_identity)

        ensure_external_identity_uniqueness('orcid', self.provider_id)

        dupe_user.reload()
        self.user.reload()

        assert_equal(dupe_user.external_identity, {})
        assert_equal(self.user.external_identity, {})

# TODO: Use mock add-on
class TestAddonUserViews(OsfTestCase):

    def setUp(self):
        super(TestAddonUserViews, self).setUp()
        self.user = AuthUserFactory()

    def test_choose_addons_add(self):
        """Add add-ons; assert that add-ons are attached to project.

        """
        url = '/api/v1/settings/addons/'
        self.app.post_json(
            url,
            {'github': True},
            auth=self.user.auth,
        ).maybe_follow()
        self.user.reload()
        assert_true(self.user.get_addon('github'))

    def test_choose_addons_remove(self):
        # Add, then delete, add-ons; assert that add-ons are not attached to
        # project.
        url = '/api/v1/settings/addons/'
        self.app.post_json(
            url,
            {'github': True},
            auth=self.user.auth,
        ).maybe_follow()
        self.app.post_json(
            url,
            {'github': False},
            auth=self.user.auth
        ).maybe_follow()
        self.user.reload()
        assert_false(self.user.get_addon('github'))


class TestConfigureMailingListViews(OsfTestCase):

    @classmethod
    def setUpClass(cls):
        super(TestConfigureMailingListViews, cls).setUpClass()
        cls._original_enable_email_subscriptions = settings.ENABLE_EMAIL_SUBSCRIPTIONS
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = True

    def test_user_unsubscribe_and_subscribe_help_mailing_list(self):
        user = AuthUserFactory()
        url = api_url_for('user_choose_mailing_lists')
        payload = {settings.OSF_HELP_LIST: False}
        res = self.app.post_json(url, payload, auth=user.auth)
        user.reload()

        assert_false(user.osf_mailing_lists[settings.OSF_HELP_LIST])

        payload = {settings.OSF_HELP_LIST: True}
        res = self.app.post_json(url, payload, auth=user.auth)
        user.reload()

        assert_true(user.osf_mailing_lists[settings.OSF_HELP_LIST])

    def test_get_notifications(self):
        user = AuthUserFactory()
        mailing_lists = dict(user.osf_mailing_lists.items() + user.mailchimp_mailing_lists.items())
        url = api_url_for('user_notifications')
        res = self.app.get(url, auth=user.auth)
        assert_equal(mailing_lists, res.json['mailing_lists'])

    def test_osf_help_mails_subscribe(self):
        user = UserFactory()
        user.osf_mailing_lists[settings.OSF_HELP_LIST] = False
        user.save()
        update_osf_help_mails_subscription(user, True)
        assert_true(user.osf_mailing_lists[settings.OSF_HELP_LIST])

    def test_osf_help_mails_unsubscribe(self):
        user = UserFactory()
        user.osf_mailing_lists[settings.OSF_HELP_LIST] = True
        user.save()
        update_osf_help_mails_subscription(user, False)
        assert_false(user.osf_mailing_lists[settings.OSF_HELP_LIST])

    @unittest.skipIf(settings.USE_CELERY, 'Subscription must happen synchronously for this test')
    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_user_choose_mailing_lists_updates_user_dict(self, mock_get_mailchimp_api):
        user = AuthUserFactory()
        list_name = 'OSF General'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': 1, 'list_name': list_name}]}
        list_id = mailchimp_utils.get_list_id_from_name(list_name)

        payload = {settings.MAILCHIMP_GENERAL_LIST: True}
        url = api_url_for('user_choose_mailing_lists')
        res = self.app.post_json(url, payload, auth=user.auth)
        user.reload()

        # check user.mailing_lists is updated
        assert_true(user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST])
        assert_equal(
            user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST],
            payload[settings.MAILCHIMP_GENERAL_LIST]
        )

        # check that user is subscribed
        mock_client.lists.subscribe.assert_called_with(id=list_id,
                                                       email={'email': user.username},
                                                       merge_vars={
                                                           'fname': user.given_name,
                                                           'lname': user.family_name,
                                                       },
                                                       double_optin=False,
                                                       update_existing=True)

    def test_get_mailchimp_get_endpoint_returns_200(self):
        url = api_url_for('mailchimp_get_endpoint')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_mailchimp_webhook_subscribe_action_does_not_change_user(self, mock_get_mailchimp_api):
        """ Test that 'subscribe' actions sent to the OSF via mailchimp
            webhooks update the OSF database.
        """
        list_id = '12345'
        list_name = 'OSF General'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': list_id, 'name': list_name}]}

        # user is not subscribed to a list
        user = AuthUserFactory()
        user.mailchimp_mailing_lists = {'OSF General': False}
        user.save()

        # user subscribes and webhook sends request to OSF
        data = {
            'type': 'subscribe',
            'data[list_id]': list_id,
            'data[email]': user.username
        }
        url = api_url_for('sync_data_from_mailchimp') + '?key=' + settings.MAILCHIMP_WEBHOOK_SECRET_KEY
        res = self.app.post(url,
                            data,
                            content_type="application/x-www-form-urlencoded",
                            auth=user.auth)

        # user field is updated on the OSF
        user.reload()
        assert_true(user.mailchimp_mailing_lists[list_name])

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
                            data,
                            content_type="application/x-www-form-urlencoded",
                            auth=user.auth)

        # user field does not change
        user.reload()
        assert_true(user.mailchimp_mailing_lists[list_name])

    @mock.patch('website.mailchimp_utils.get_mailchimp_api')
    def test_sync_data_from_mailchimp_unsubscribes_user(self, mock_get_mailchimp_api):
        list_id = '12345'
        list_name = 'OSF General'
        mock_client = mock.MagicMock()
        mock_get_mailchimp_api.return_value = mock_client
        mock_client.lists.list.return_value = {'data': [{'id': list_id, 'name': list_name}]}

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
                            data,
                            content_type="application/x-www-form-urlencoded",
                            auth=user.auth)

        # user field is updated on the OSF
        user.reload()
        assert_false(user.mailchimp_mailing_lists[list_name])

    def test_sync_data_from_mailchimp_fails_without_secret_key(self):
        user = AuthUserFactory()
        payload = {'values': {'type': 'unsubscribe',
                              'data': {'list_id': '12345',
                                       'email': 'freddie@cos.io'}}}
        url = api_url_for('sync_data_from_mailchimp')
        res = self.app.post_json(url, payload, auth=user.auth, expect_errors=True)
        assert_equal(res.status_code, http.UNAUTHORIZED)

    @classmethod
    def tearDownClass(cls):
        super(TestConfigureMailingListViews, cls).tearDownClass()
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = cls._original_enable_email_subscriptions

# TODO: Move to OSF Storage
class TestFileViews(OsfTestCase):

    def setUp(self):
        super(TestFileViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=True)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_grid_data(self):
        url = self.project.api_url_for('grid_data')
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, http.OK)
        expected = rubeus.to_hgrid(self.project, auth=Auth(self.user))
        data = res.json['data']
        assert_equal(len(data), len(expected))


class TestTagViews(OsfTestCase):

    def setUp(self):
        super(TestTagViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    @unittest.skip('Tags endpoint disabled for now.')
    def test_tag_get_returns_200(self):
        url = web_url_for('project_tag', tag='foo')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)


class TestReorderComponents(OsfTestCase):

    def setUp(self):
        super(TestReorderComponents, self).setUp()
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
                '{0}'.format(self.private_component._id),
                '{0}'.format(self.public_component._id),
            ]
        }
        url = self.project.api_url_for('project_reorder_components')
        res = self.app.post_json(url, payload, auth=self.contrib.auth)
        assert_equal(res.status_code, 200)


class TestWikiWidgetViews(OsfTestCase):

    def setUp(self):
        super(TestWikiWidgetViews, self).setUp()

        # project with no home wiki page
        self.project = ProjectFactory()
        self.read_only_contrib = AuthUserFactory()
        self.project.add_contributor(self.read_only_contrib, permissions='read')
        self.noncontributor = AuthUserFactory()

        # project with no home wiki content
        self.project2 = ProjectFactory(creator=self.project.creator)
        self.project2.add_contributor(self.read_only_contrib, permissions='read')
        self.project2.update_node_wiki(name='home', content='', auth=Auth(self.project.creator))

    def test_show_wiki_for_contributors_when_no_wiki_or_content(self):
        contrib = self.project.contributor_set.get(user=self.project.creator)
        assert_true(_should_show_wiki_widget(self.project, contrib))
        assert_true(_should_show_wiki_widget(self.project2, contrib))

    def test_show_wiki_is_false_for_read_contributors_when_no_wiki_or_content(self):
        contrib = self.project.contributor_set.get(user=self.read_only_contrib)
        assert_false(_should_show_wiki_widget(self.project, contrib))
        assert_false(_should_show_wiki_widget(self.project2, contrib))

    def test_show_wiki_is_false_for_noncontributors_when_no_wiki_or_content(self):
        assert_false(_should_show_wiki_widget(self.project, None))


class TestProjectCreation(OsfTestCase):

    def setUp(self):
        super(TestProjectCreation, self).setUp()
        self.creator = AuthUserFactory()
        self.url = api_url_for('project_new_post')
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user1)
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()

    def tearDown(self):
        super(TestProjectCreation, self).tearDown()

    def test_needs_title(self):
        res = self.app.post_json(self.url, {}, auth=self.creator.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_create_component_strips_html(self):
        user = AuthUserFactory()
        project = ProjectFactory(creator=user)
        url = web_url_for('project_new_node', pid=project._id)
        post_data = {'title': '<b>New <blink>Component</blink> Title</b>', 'category': ''}
        request = self.app.post(url, post_data, auth=user.auth).follow()
        project.reload()
        child = project.nodes[0]
        # HTML has been stripped
        assert_equal(child.title, 'New Component Title')

    def test_strip_html_from_title(self):
        payload = {
            'title': 'no html <b>here</b>'
        }
        res = self.app.post_json(self.url, payload, auth=self.creator.auth)
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert_true(node)
        assert_equal('no html here', node.title)

    def test_only_needs_title(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post_json(self.url, payload, auth=self.creator.auth)
        assert_equal(res.status_code, 201)

    def test_title_must_be_one_long(self):
        payload = {
            'title': ''
        }
        res = self.app.post_json(
            self.url, payload, auth=self.creator.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_title_must_be_less_than_200(self):
        payload = {
            'title': ''.join([str(x) for x in xrange(0, 250)])
        }
        res = self.app.post_json(
            self.url, payload, auth=self.creator.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_fails_to_create_project_with_whitespace_title(self):
        payload = {
            'title': '   '
        }
        res = self.app.post_json(
            self.url, payload, auth=self.creator.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_creates_a_project(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post_json(self.url, payload, auth=self.creator.auth)
        assert_equal(res.status_code, 201)
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert_true(node)
        assert_true(node.title, 'Im a real title')

    def test_create_component_add_contributors_admin(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, post_data, auth=self.user1.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert_equal(child.title, 'New Component With Contributors Title')
        assert_in(self.user1, child.contributors)
        assert_in(self.user2, child.contributors)
        # check redirect url
        assert_in('/contributors/', res.location)

    def test_create_component_with_contributors_read_write(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=['read', 'write'])
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, post_data, auth=non_admin.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert_equal(child.title, 'New Component With Contributors Title')
        assert_in(non_admin, child.contributors)
        assert_in(self.user1, child.contributors)
        assert_in(self.user2, child.contributors)
        assert_equal(child.get_permissions(non_admin), ['read', 'write', 'admin'])
        # check redirect url
        assert_in('/contributors/', res.location)

    def test_create_component_with_contributors_read(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        non_admin = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=['read'])
        self.project.save()
        post_data = {'title': 'New Component With Contributors Title', 'category': '', 'inherit_contributors': True}
        res = self.app.post(url, post_data, auth=non_admin.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_create_component_add_no_contributors(self):
        url = web_url_for('project_new_node', pid=self.project._id)
        post_data = {'title': 'New Component With Contributors Title', 'category': ''}
        res = self.app.post(url, post_data, auth=self.user1.auth)
        self.project.reload()
        child = self.project.nodes[0]
        assert_equal(child.title, 'New Component With Contributors Title')
        assert_in(self.user1, child.contributors)
        assert_not_in(self.user2, child.contributors)
        # check redirect url
        assert_not_in('/contributors/', res.location)

    def test_new_project_returns_serialized_node_data(self):
        payload = {
            'title': 'Im a real title'
        }
        res = self.app.post_json(self.url, payload, auth=self.creator.auth)
        assert_equal(res.status_code, 201)
        node = res.json['newNode']
        assert_true(node)
        assert_equal(node['title'], 'Im a real title')

    def test_description_works(self):
        payload = {
            'title': 'Im a real title',
            'description': 'I describe things!'
        }
        res = self.app.post_json(self.url, payload, auth=self.creator.auth)
        assert_equal(res.status_code, 201)
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert_true(node)
        assert_true(node.description, 'I describe things!')

    def test_can_template(self):
        other_node = ProjectFactory(creator=self.creator)
        payload = {
            'title': 'Im a real title',
            'template': other_node._id
        }
        res = self.app.post_json(self.url, payload, auth=self.creator.auth)
        assert_equal(res.status_code, 201)
        node = AbstractNode.load(res.json['projectUrl'].replace('/', ''))
        assert_true(node)
        assert_true(node.template_node, other_node)

    def test_project_before_template_no_addons(self):
        project = ProjectFactory()
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert_equal(res.json['prompts'], [])

    def test_project_before_template_with_addons(self):
        project = ProjectWithAddonFactory(addon='box')
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert_in('Box', res.json['prompts'])

    def test_project_new_from_template_non_user(self):
        project = ProjectFactory()
        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=None)
        assert_equal(res.status_code, 302)
        res2 = res.follow(expect_errors=True)
        assert_equal(res2.status_code, 301)
        assert_equal(res2.request.path, '/login')

    def test_project_new_from_template_public_non_contributor(self):
        non_contributor = AuthUserFactory()
        project = ProjectFactory(is_public=True)
        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=non_contributor.auth)
        assert_equal(res.status_code, 201)

    def test_project_new_from_template_contributor(self):
        contributor = AuthUserFactory()
        project = ProjectFactory(is_public=False)
        project.add_contributor(contributor)
        project.save()

        url = api_url_for('project_new_from_template', nid=project._id)
        res = self.app.post(url, auth=contributor.auth)
        assert_equal(res.status_code, 201)


class TestUnconfirmedUserViews(OsfTestCase):

    def test_can_view_profile(self):
        user = UnconfirmedUserFactory()
        url = web_url_for('profile_view_id', uid=user._id)
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

class TestStaticFileViews(OsfTestCase):

    def test_robots_dot_txt(self):
        res = self.app.get('/robots.txt')
        assert_equal(res.status_code, 200)
        assert_in('User-agent', res)
        assert_in('text/plain', res.headers['Content-Type'])

    def test_favicon(self):
        res = self.app.get('/favicon.ico')
        assert_equal(res.status_code, 200)
        assert_in('image/vnd.microsoft.icon', res.headers['Content-Type'])

    def test_getting_started_page(self):
        res = self.app.get('/getting-started/')
        assert_equal(res.status_code, 302)
        assert_equal(res.location, 'http://help.osf.io/')
    def test_help_redirect(self):
        res = self.app.get('/help/')
        assert_equal(res.status_code,302)


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
            res = self.app.post(url, payload)
            assert_equal(res.status_code, 302)

        assert_equal(mock_signals.signals_sent(), set([auth.signals.user_confirmed]))

    def test_confirm_user_signal_called_when_user_confirms_email(self):
        unconfirmed_user = UnconfirmedUserFactory()
        unconfirmed_user.save()

        # user goes to email confirmation link
        token = unconfirmed_user.get_confirmation_token(unconfirmed_user.username)
        with capture_signals() as mock_signals:
            url = web_url_for('confirm_email_get', uid=unconfirmed_user._id, token=token)
            res = self.app.get(url)
            assert_equal(res.status_code, 302)

        assert_equal(mock_signals.signals_sent(), set([auth.signals.user_confirmed]))


# copied from tests/test_comments.py
class TestCommentViews(OsfTestCase):

    def setUp(self):
        super(TestCommentViews, self).setUp()
        self.project = ProjectFactory(is_public=True)
        self.user = AuthUserFactory()
        self.project.add_contributor(self.user)
        self.project.save()
        self.user.save()

    def test_view_project_comments_updates_user_comments_view_timestamp(self):
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put_json(url, {
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
        res = self.app.put_json(url, {
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)

        non_contributor.reload()
        assert_not_in(self.project._id, non_contributor.comments_viewed_timestamp)

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
        res = self.app.put_json(url, {
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
            self.app.put_json(url, payload, auth=user.auth)
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
        super(TestResetPassword, self).setUp()
        self.user = AuthUserFactory()
        self.another_user = AuthUserFactory()
        self.osf_key_v2 = generate_verification_key(verification_type='password')
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
            token=generate_verification_key()
        )
        self.get_url_invalid_user = web_url_for(
            'reset_password_get',
            uid=self.another_user._id,
            token=self.osf_key_v2['token']
        )

    # successfully load reset password page
    def test_reset_password_view_returns_200(self):
        res = self.app.get(self.get_url)
        assert_equal(res.status_code, 200)

    # raise http 400 error
    def test_reset_password_view_raises_400(self):
        res = self.app.get(self.get_url_invalid_key, expect_errors=True)
        assert_equal(res.status_code, 400)

        res = self.app.get(self.get_url_invalid_user, expect_errors=True)
        assert_equal(res.status_code, 400)

        self.user.verification_key_v2['expires'] = timezone.now()
        self.user.save()
        res = self.app.get(self.get_url, expect_errors=True)
        assert_equal(res.status_code, 400)

    # successfully reset password
    @mock.patch('framework.auth.cas.CasClient.service_validate')
    def test_can_reset_password_if_form_success(self, mock_service_validate):
        # load reset password page and submit email
        res = self.app.get(self.get_url)
        form = res.forms['resetPasswordForm']
        form['password'] = 'newpassword'
        form['password2'] = 'newpassword'
        res = form.submit()

        # check request URL is /resetpassword with username and new verification_key_v2 token
        request_url_path = res.request.path
        assert_in('resetpassword', request_url_path)
        assert_in(self.user._id, request_url_path)
        assert_not_in(self.user.verification_key_v2['token'], request_url_path)

        # check verification_key_v2 for OSF is destroyed and verification_key for CAS is in place
        self.user.reload()
        assert_equal(self.user.verification_key_v2, {})
        assert_not_equal(self.user.verification_key, None)

        # check redirection to CAS login with username and the new verification_key(CAS)
        assert_equal(res.status_code, 302)
        location = res.headers.get('Location')
        assert_true('login?service=' in location)
        assert_true('username={}'.format(urllib.quote(self.user.username, safe='@')) in location)
        assert_true('verification_key={}'.format(self.user.verification_key) in location)

        # check if password was updated
        self.user.reload()
        assert_true(self.user.check_password('newpassword'))

        # check if verification_key is destroyed after service validation
        mock_service_validate.return_value = cas.CasResponse(
            authenticated=True,
            user=self.user._id,
            attributes={'accessToken': fake.md5()}
        )
        ticket = fake.md5()
        service_url = 'http://accounts.osf.io/?ticket=' + ticket
        cas.make_response_from_ticket(ticket, service_url)
        self.user.reload()
        assert_equal(self.user.verification_key, None)

    #  log users out before they land on reset password page
    def test_reset_password_logs_out_user(self):
        # visit reset password link while another user is logged in
        res = self.app.get(self.get_url, auth=self.another_user.auth)
        # check redirection to CAS logout
        assert_equal(res.status_code, 302)
        location = res.headers.get('Location')
        assert_not_in('reauth', location)
        assert_in('logout?service=', location)
        assert_in('resetpassword', location)

class TestIndexView(OsfTestCase):

    def setUp(self):
        super(TestIndexView, self).setUp()

        self.inst_one = InstitutionFactory()
        self.inst_two = InstitutionFactory()
        self.inst_three = InstitutionFactory()
        self.inst_four = InstitutionFactory()
        self.inst_five = InstitutionFactory()

        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.inst_one)
        self.user.affiliated_institutions.add(self.inst_two)

        # tests 5 affiliated, non-registered, public projects
        for i in range(settings.INSTITUTION_DISPLAY_NODE_THRESHOLD):
            node = ProjectFactory(creator=self.user, is_public=True)
            node.affiliated_institutions.add(self.inst_one)

        # tests 4 affiliated, non-registered, public projects
        for i in range(settings.INSTITUTION_DISPLAY_NODE_THRESHOLD - 1):
            node = ProjectFactory(creator=self.user, is_public=True)
            node.affiliated_institutions.add(self.inst_two)

        # tests 5 affiliated, registered, public projects
        for i in range(settings.INSTITUTION_DISPLAY_NODE_THRESHOLD):
            registration = RegistrationFactory(creator=self.user, is_public=True)
            registration.affiliated_institutions.add(self.inst_three)

        # tests 5 affiliated, non-registered public components
        for i in range(settings.INSTITUTION_DISPLAY_NODE_THRESHOLD):
            node = NodeFactory(creator=self.user, is_public=True)
            node.affiliated_institutions.add(self.inst_four)

        # tests 5 affiliated, non-registered, private projects
        for i in range(settings.INSTITUTION_DISPLAY_NODE_THRESHOLD):
            node = ProjectFactory(creator=self.user)
            node.affiliated_institutions.add(self.inst_five)

    def test_dashboard_institutions(self):
        with mock.patch('website.views.get_current_user_id', return_value=self.user._id):
            institution_ids = [
                institution['id']
                for institution in index()['dashboard_institutions']
            ]
            assert_equal(len(institution_ids), 2)
            assert_in(self.inst_one._id, institution_ids)
            assert_not_in(self.inst_two._id, institution_ids)
            assert_not_in(self.inst_three._id, institution_ids)
            assert_in(self.inst_four._id, institution_ids)
            assert_not_in(self.inst_five._id, institution_ids)


class TestResolveGuid(OsfTestCase):
    def setUp(self):
        super(TestResolveGuid, self).setUp()

    def test_preprint_provider_without_domain(self):
        provider = PreprintProviderFactory(domain='')
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.request.path,
            '/{}/'.format(preprint._id)
        )

    def test_preprint_provider_with_domain_without_redirect(self):
        domain = 'https://test.com/'
        provider = PreprintProviderFactory(_id='test', domain=domain, domain_redirect_enabled=False)
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.request.path,
            '/{}/'.format(preprint._id)
        )

    def test_preprint_provider_with_domain_with_redirect(self):
        domain = 'https://test.com/'
        provider = PreprintProviderFactory(_id='test', domain=domain, domain_redirect_enabled=True)
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)

        assert_is_redirect(res)
        assert_equal(res.status_code, 301)
        assert_equal(
            res.headers['location'],
            '{}{}/'.format(domain, preprint._id)
        )

        assert_equal(
            res.request.path,
            '/{}/'.format(preprint._id)
        )



    def test_preprint_provider_with_osf_domain(self):
        provider = PreprintProviderFactory(_id='osf', domain='https://osf.io/')
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.request.path,
            '/{}/'.format(preprint._id)
        )

    def test_deleted_quick_file_gone(self):
        user = AuthUserFactory()
        quickfiles = QuickFilesNode.objects.get(creator=user)
        osfstorage = quickfiles.get_addon('osfstorage')
        root = osfstorage.get_root()
        test_file = root.append_file('soon_to_be_deleted.txt')
        guid = test_file.get_guid(create=True)._id
        test_file.delete()

        url = web_url_for('resolve_guid', _guid=True, guid=guid)
        res = self.app.get(url, expect_errors=True)

        assert_equal(res.status_code, http.GONE)
        assert_equal(res.request.path, '/{}/'.format(guid))

class TestConfirmationViewBlockBingPreview(OsfTestCase):

    def setUp(self):

        super(TestConfirmationViewBlockBingPreview, self).setUp()
        self.user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/534+ (KHTML, like Gecko) BingPreview/1.0b'

    # reset password link should fail with BingPreview
    def test_reset_password_get_returns_403(self):

        user = UserFactory()
        osf_key_v2 = generate_verification_key(verification_type='password')
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
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)

    # new user confirm account should fail with BingPreview
    def test_confirm_email_get_new_user_returns_403(self):

        user = OSFUser.create_unconfirmed('unconfirmed@cos.io', 'abCD12#$', 'Unconfirmed User')
        user.save()
        confirm_url = user.get_confirmation_url('unconfirmed@cos.io', external=False)
        res = self.app.get(
            confirm_url,
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)

    # confirmation for adding new email should fail with BingPreview
    def test_confirm_email_add_email_returns_403(self):

        user = UserFactory()
        user.add_unconfirmed_email('unconfirmed@cos.io')
        user.save()

        confirm_url = user.get_confirmation_url('unconfirmed@cos.io', external=False) + '?logout=1'
        res = self.app.get(
            confirm_url,
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)

    # confirmation for merging accounts should fail with BingPreview
    def test_confirm_email_merge_account_returns_403(self):

        user = UserFactory()
        user_to_be_merged = UserFactory()
        user.add_unconfirmed_email(user_to_be_merged.username)
        user.save()

        confirm_url = user.get_confirmation_url(user_to_be_merged.username, external=False) + '?logout=1'
        res = self.app.get(
            confirm_url,
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)

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
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)

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
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)

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
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)

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
            expect_errors=True,
            headers={
                'User-Agent': self.user_agent,
            }
        )
        assert_equal(res.status_code, 403)


if __name__ == '__main__':
    unittest.main()
