#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Views tests for the OSF."""

from __future__ import absolute_import

import datetime as dt
import httplib as http
import json
import math
import time
import unittest
import urllib
import datetime

import mock
from nose.tools import *  # noqa PEP8 asserts

from modularodm import Q
from modularodm.exceptions import ValidationError

from framework import auth
from framework.auth import User, Auth
from framework.auth.exceptions import InvalidTokenError
from framework.auth.utils import impute_names_model
from framework.celery_tasks import handlers
from framework.exceptions import HTTPError
from tests.base import (
    assert_is_redirect,
    capture_signals,
    fake,
    get_default_metaschema,
    OsfTestCase,
)
from tests.factories import (
    ApiOAuth2ApplicationFactory, ApiOAuth2PersonalTokenFactory, AuthUserFactory,
    BookmarkCollectionFactory, CollectionFactory, MockAddonNodeSettings, NodeFactory,
    NodeLogFactory, PrivateLinkFactory, ProjectWithAddonFactory, ProjectFactory,
    RegistrationFactory, UnconfirmedUserFactory, UnregUserFactory, UserFactory, WatchConfigFactory,
)
from tests.test_features import requires_search
from website import mailchimp_utils
from website import mails, settings
from website.addons.github.tests.factories import GitHubAccountFactory
from website.models import Node, NodeLog, Pointer
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
from website.util import permissions, rubeus


class Addon(MockAddonNodeSettings):
    @property
    def complete(self):
        return True

    def archive_errors(self):
        return 'Error'


class Addon2(MockAddonNodeSettings):
    @property
    def complete(self):
        return True

    def archive_errors(self):
        return 'Error'


class TestViewingProjectWithPrivateLink(OsfTestCase):

    def setUp(self):
        super(TestViewingProjectWithPrivateLink, self).setUp()
        self.user = AuthUserFactory()  # Is NOT a contributor
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory()
        self.link.nodes.append(self.project)
        self.link.save()
        self.project_url = self.project.web_url_for('view_project')

    def test_edit_private_link_empty(self):
        node = ProjectFactory(creator=self.user)
        link = PrivateLinkFactory()
        link.nodes.append(node)
        link.save()
        url = node.api_url_for("project_private_link_edit")
        res = self.app.put_json(url, {'pk': link._id, 'value': ''}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Title cannot be blank', res.body)

    def test_edit_private_link_invalid(self):
        node = ProjectFactory(creator=self.user)
        link = PrivateLinkFactory()
        link.nodes.append(node)
        link.save()
        url = node.api_url_for("project_private_link_edit")
        res = self.app.put_json(url, {'pk': link._id, 'value': '<a></a>'}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Invalid link name.', res.body)

    @mock.patch('framework.auth.core.Auth.private_link')
    def test_can_be_anonymous_for_public_project(self, mock_property):
        mock_property.return_value(mock.MagicMock())
        mock_property.anonymous = True
        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.append(self.project)
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
        anonymous_link.nodes.append(self.project)
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
        link.nodes.append(self.project)
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

    ADDONS_UNDER_TEST = {
        'addon1': {
            'node_settings': Addon,
        },
        'addon2': {
            'node_settings': Addon2,
        },
    }

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
            title="Ham",
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()

        self.project2 = ProjectFactory(
            title="Tofu",
            description='Glazed',
            creator=self.user1
        )
        self.project2.add_contributor(self.user2, auth=Auth(self.user1))
        self.project2.save()

    def test_edit_title_empty(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for("edit_node")
        res = self.app.post_json(url, {'name': 'title', 'value': ''}, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Title cannot be blank', res.body)

    def test_edit_title_invalid(self):
        node = ProjectFactory(creator=self.user1)
        url = node.api_url_for("edit_node")
        res = self.app.post_json(url, {'name': 'title', 'value': '<a></a>'}, auth=self.user1.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_in('Invalid title.', res.body)

    def test_cannot_remove_only_visible_contributor(self):
        self.project.visible_contributor_ids.remove(self.user1._id)
        self.project.save()
        url = self.project.api_url_for('project_remove_contributor')
        res = self.app.post_json(
            url, {'contributorID': self.user2._id,
                  'nodeIDs': [self.project._id]}, auth=self.auth, expect_errors=True
        )
        assert_equal(res.status_code, http.FORBIDDEN)
        assert_equal(res.json['message_long'], 'Must have at least one bibliographic contributor')
        assert_true(self.project.is_contributor(self.user2))

    def test_remove_only_visible_contributor_return_false(self):
        self.project.visible_contributor_ids.remove(self.user1._id)
        self.project.save()
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
        url = "/api/v1/project/{0}/edit/".format(self.project._id)
        self.app.post_json(url,
                           {"name": "description", "value": "Deep-fried"},
                           auth=self.auth)
        self.project.reload()
        assert_equal(self.project.description, "Deep-fried")

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
        assert_equal(data['node']['watched_count'], 0)
        assert_true(data['user']['is_contributor'])
        assert_equal(data['node']['description'], self.project.description)
        assert_equal(data['node']['url'], self.project.url)
        assert_equal(data['node']['tags'], [t._primary_key for t in self.project.tags])
        assert_in('forked_date', data['node'])
        assert_in('watched_count', data['node'])
        assert_in('registered_from_url', data['node'])
        # TODO: Test "parent" and "user" output

    def test_add_contributor_post(self):
        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        user2 = UserFactory()
        user3 = UserFactory()
        url = "/api/v1/project/{0}/contributors/".format(project._id)

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
            content_type="application/json",
            auth=self.auth,
        ).maybe_follow()
        project.reload()
        assert_in(user2._id, project.contributors)
        # A log event was added
        assert_equal(project.logs[-1].action, "contributor_added")
        assert_equal(len(project.contributors), 3)
        assert_in(user2._id, project.permissions)
        assert_in(user3._id, project.permissions)
        assert_equal(project.permissions[user2._id], ['read', 'write', 'admin'])
        assert_equal(project.permissions[user3._id], ['read', 'write'])

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
            fullname=fake.name(), email=fake.email(),
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
            project.visible_contributors,
            [project.creator, unregistered_user, reg_user1]
        )

    def test_project_remove_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {"contributorID": self.user2._id,
                   "nodeIDs": [self.project._id]}
        self.app.post(url, json.dumps(payload),
                      content_type="application/json",
                      auth=self.auth).maybe_follow()
        self.project.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_removed")

    def test_multiple_project_remove_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {"contributorID": self.user2._id,
                   "nodeIDs": [self.project._id, self.project2._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        self.project.reload()
        self.project2.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        assert_not_in('/dashboard/', res.json)

        assert_not_in(self.user2._id, self.project2.contributors)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_removed")

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
                     'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.'
                     )
        assert_in(self.user1._id, self.project.contributors)

    def test_project_remove_fake_contributor(self):
        url = self.project.api_url_for('project_remove_contributor')
        # User 1 removes user2
        payload = {"contributorID": 'badid',
                   "nodeIDs": [self.project._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type="application/json",
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
        payload = {"contributorID": self.user1._id,
                   "nodeIDs": [self.project._id]}
        res = self.app.post(url, json.dumps(payload),
                            content_type="application/json",
                            expect_errors=True,
                            auth=self.auth).maybe_follow()

        self.project.reload()
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Could not remove contributor.')
        assert_in(self.user1._id, self.project.contributors)

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
            fullname=fake.name(), email=fake.email(),
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
        url = "/api/v1/project/{0}/edit/".format(self.project._id)
        # The title is changed though posting form data
        self.app.post_json(url, {"name": "title", "value": "Bacon"},
                           auth=self.auth).maybe_follow()
        self.project.reload()
        # The title was changed
        assert_equal(self.project.title, "Bacon")
        # A log event was saved
        assert_equal(self.project.logs[-1].action, "edit_title")

    def test_make_public(self):
        self.project.is_public = False
        self.project.save()
        url = "/api/v1/project/{0}/permissions/public/".format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_true(self.project.is_public)
        assert_equal(res.json['status'], 'success')

    def test_make_private(self):
        self.project.is_public = True
        self.project.save()
        url = "/api/v1/project/{0}/permissions/private/".format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_false(self.project.is_public)
        assert_equal(res.json['status'], 'success')

    def test_cant_make_public_if_not_admin(self):
        non_admin = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=['read', 'write'])
        self.project.is_public = False
        self.project.save()
        url = "/api/v1/project/{0}/permissions/public/".format(self.project._id)
        res = self.app.post_json(
            url, {}, auth=non_admin.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.FORBIDDEN)
        assert_false(self.project.is_public)

    def test_cant_make_private_if_not_admin(self):
        non_admin = AuthUserFactory()
        self.project.add_contributor(non_admin, permissions=['read', 'write'])
        self.project.is_public = True
        self.project.save()
        url = "/api/v1/project/{0}/permissions/private/".format(self.project._id)
        res = self.app.post_json(
            url, {}, auth=non_admin.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.FORBIDDEN)
        assert_true(self.project.is_public)

    def test_add_tag(self):
        url = self.project.api_url_for('project_add_tag')
        self.app.post_json(url, {'tag': "foo'ta#@%#%^&g?"}, auth=self.auth)
        self.project.reload()
        assert_in("foo'ta#@%#%^&g?", self.project.tags)
        assert_equal("foo'ta#@%#%^&g?", self.project.logs[-1].params['tag'])

    def test_remove_tag(self):
        self.project.add_tag("foo'ta#@%#%^&g?", auth=self.consolidate_auth1, save=True)
        assert_in("foo'ta#@%#%^&g?", self.project.tags)
        url = self.project.api_url_for("project_remove_tag")
        self.app.delete_json(url, {"tag": "foo'ta#@%#%^&g?"}, auth=self.auth)
        self.project.reload()
        assert_not_in("foo'ta#@%#%^&g?", self.project.tags)
        assert_equal("tag_removed", self.project.logs[-1].action)
        assert_equal("foo'ta#@%#%^&g?", self.project.logs[-1].params['tag'])

    # Regression test for #OSF-5257
    def test_removal_empty_tag_throws_error(self):
        url = self.project.api_url_for('project_remove_tag')
        res= self.app.delete_json(url, {'tag': ''}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)

    # Regression test for #OSF-5257
    def test_removal_unknown_tag_throws_error(self):
        self.project.add_tag('narf', auth=self.consolidate_auth1, save=True)
        url = self.project.api_url_for('project_remove_tag')
        res= self.app.delete_json(url, {'tag': 'troz'}, auth=self.auth, expect_errors=True)
        assert_equal(res.status_code, http.CONFLICT)

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/1478
    @mock.patch('website.archiver.tasks.archive')
    def test_registered_projects_contributions(self, mock_archive):
        # register a project
        self.project.register_node(get_default_metaschema(), Auth(user=self.project.creator), '', None)
        # get the first registered project of a project
        url = self.project.api_url_for('get_registrations')
        res = self.app.get(url, auth=self.auth)
        data = res.json
        pid = data['nodes'][0]['id']
        url2 = api_url_for('get_summary', pid=pid)
        # count contributions
        res2 = self.app.get(url2, auth=self.auth)
        data = res2.json
        assert_is_not_none(data['summary']['nlogs'])

    def test_forks_contributions(self):
        # fork a project
        self.project.fork_node(Auth(user=self.project.creator))
        # get the first forked project of a project
        url = self.project.api_url_for('get_forks')
        res = self.app.get(url, auth=self.auth)
        data = res.json
        pid = data['nodes'][0]['id']
        url2 = api_url_for('get_summary', pid=pid)
        # count contributions
        res2 = self.app.get(url2, auth=self.auth)
        data = res2.json
        assert_is_not_none(data['summary']['nlogs'])

    @mock.patch('framework.transactions.commands.begin')
    @mock.patch('framework.transactions.commands.rollback')
    @mock.patch('framework.transactions.commands.commit')
    def test_get_logs(self, *mock_commands):
        # Add some logs
        for _ in range(5):
            self.project.add_log('file_added', params={'node': self.project._id}, auth=self.consolidate_auth1)

        self.project.save()
        url = self.project.api_url_for('get_logs')
        res = self.app.get(url, auth=self.auth)
        for mock_command in mock_commands:
            assert_false(mock_command.called)
        self.project.reload()
        data = res.json
        assert_equal(len(data['logs']), len(self.project.logs))
        assert_equal(data['total'], len(self.project.logs))
        assert_equal(data['page'], 0)
        assert_equal(data['pages'], 1)
        most_recent = data['logs'][0]
        assert_equal(most_recent['action'], 'file_added')

    def test_get_logs_invalid_page_input(self):
        url = self.project.api_url_for('get_logs')
        invalid_input = 'invalid page'
        res = self.app.get(
            url, {'page': invalid_input}, auth=self.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)
        assert_equal(
            res.json['message_long'],
            'Invalid value for "page".'
        )

    def test_get_logs_negative_page_num(self):
        url = self.project.api_url_for('get_logs')
        invalid_input = -1
        res = self.app.get(
            url, {'page': invalid_input}, auth=self.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)
        assert_equal(
            res.json['message_long'],
            'Invalid value for "page".'
        )

    def test_get_logs_page_num_beyond_limit(self):
        url = self.project.api_url_for('get_logs')
        size = 10
        page_num = math.ceil(len(self.project.logs) / float(size))
        res = self.app.get(
            url, {'page': page_num}, auth=self.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)
        assert_equal(
            res.json['message_long'],
            'Invalid value for "page".'
        )

    def test_get_logs_with_count_param(self):
        # Add some logs
        for _ in range(5):
            self.project.add_log('file_added', params={'node': self.project._id}, auth=self.consolidate_auth1)

        self.project.save()
        url = self.project.api_url_for('get_logs')
        res = self.app.get(url, {'count': 3}, auth=self.auth)
        assert_equal(len(res.json['logs']), 3)
        # 1 project create log, 1 add contributor log, then 5 generated logs
        assert_equal(res.json['total'], 5 + 2)
        assert_equal(res.json['page'], 0)
        assert_equal(res.json['pages'], 3)

    def test_get_logs_defaults_to_ten(self):
        # Add some logs
        for _ in range(12):
            self.project.add_log('file_added', params={'node': self.project._id}, auth=self.consolidate_auth1)

        self.project.save()
        url = self.project.api_url_for('get_logs')
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), 10)
        # 1 project create log, 1 add contributor log, then 5 generated logs
        assert_equal(res.json['total'], 12 + 2)
        assert_equal(res.json['page'], 0)
        assert_equal(res.json['pages'], 2)

    def test_get_more_logs(self):
        # Add some logs
        for _ in range(12):
            self.project.add_log('file_added', params={'node': self.project._id}, auth=self.consolidate_auth1)

        self.project.save()
        url = self.project.api_url_for('get_logs')
        res = self.app.get(url, {"page": 1}, auth=self.auth)
        assert_equal(len(res.json['logs']), 4)
        # 1 project create log, 1 add contributor log, then 12 generated logs
        assert_equal(res.json['total'], 12 + 2)
        assert_equal(res.json['page'], 1)
        assert_equal(res.json['pages'], 2)

    def test_logs_private(self):
        """Add logs to a public project, then to its private component. Get
        the ten most recent logs; assert that ten logs are returned and that
        all belong to the project and not its component.

        """
        # Add some logs
        for _ in range(15):
            self.project.add_log(
                auth=self.consolidate_auth1,
                action='file_added',
                params={'node': self.project._id}
            )
        self.project.is_public = True
        self.project.save()
        child = NodeFactory(parent=self.project)
        for _ in range(5):
            child.add_log(
                auth=self.consolidate_auth1,
                action='file_added',
                params={'node': child._id}
            )

        url = self.project.api_url_for('get_logs')
        res = self.app.get(url).maybe_follow()
        assert_equal(len(res.json['logs']), 10)
        # 1 project create log, 1 add contributor log, then 15 generated logs
        assert_equal(res.json['total'], 15 + 2)
        assert_equal(res.json['page'], 0)
        assert_equal(res.json['pages'], 2)
        assert_equal(
            [self.project._id] * 10,
            [
                log['params']['node']
                for log in res.json['logs']
            ]
        )

    def test_can_view_public_log_from_private_project(self):
        project = ProjectFactory(is_public=True)
        fork = project.fork_node(auth=self.consolidate_auth1)
        url = fork.api_url_for('get_logs')
        res = self.app.get(url, auth=self.auth)
        assert_equal(
            [each['action'] for each in res.json['logs']],
            ['node_forked', 'project_created'],
        )
        project.is_public = False
        project.save()
        res = self.app.get(url, auth=self.auth)
        assert_equal(
            [each['action'] for each in res.json['logs']],
            ['node_forked', 'project_created'],
        )

    def test_for_private_component_log(self):
        for _ in range(5):
            self.project.add_log(
                auth=self.consolidate_auth1,
                action='file_added',
                params={'node': self.project._id}
            )
        self.project.is_public = True
        self.project.save()
        child = NodeFactory(parent=self.project)
        child.is_public = False
        child.set_title("foo", auth=self.consolidate_auth1)
        child.set_title("bar", auth=self.consolidate_auth1)
        child.save()
        url = self.project.api_url_for('get_logs')
        res = self.app.get(url).maybe_follow()
        assert_equal(len(res.json['logs']), 7)
        assert_not_in(
            child._id,
            [
                log['params']['node']
                for log in res.json['logs']
            ]
        )

    def test_remove_project(self):
        url = self.project.api_url
        res = self.app.delete_json(url, {}, auth=self.auth).maybe_follow()
        self.project.reload()
        assert_equal(self.project.is_deleted, True)
        assert_in('url', res.json)
        assert_equal(res.json['url'], '/dashboard/')

    def test_suspended_project(self):
        node = NodeFactory(parent=self.project, creator=self.user1)
        node.remove_node(Auth(self.user1))
        node.suspended = True
        node.save()
        url = node.api_url
        res = self.app.get(url, auth=Auth(self.user1), expect_errors=True)
        assert_equal(res.status_code, 451)

    def test_private_link_edit_name(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        assert_equal(link.name, "link")
        url = self.project.api_url + 'private_link/edit/'
        self.app.put_json(
            url,
            {'pk': link._id, "value": "new name"},
            auth=self.auth,
        ).maybe_follow()
        self.project.reload()
        link.reload()
        assert_equal(link.name, "new name")

    def test_remove_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
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

    def test_watch_and_unwatch(self):
        url = self.project.api_url_for('togglewatch_post')
        self.app.post_json(url, {}, auth=self.auth)
        res = self.app.get(self.project.api_url, auth=self.auth)
        assert_equal(res.json['node']['watched_count'], 1)
        self.app.post_json(url, {}, auth=self.auth)
        res = self.app.get(self.project.api_url, auth=self.auth)
        assert_equal(res.json['node']['watched_count'], 0)

    def test_view_project_returns_whether_to_show_wiki_widget(self):
        user = AuthUserFactory()
        project = ProjectFactory.build(creator=user, is_public=True)
        project.add_contributor(user)
        project.save()

        url = project.api_url_for('view_project')
        res = self.app.get(url, auth=user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('show_wiki_widget', res.json['user'])

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

    def test_statistic_page_redirect(self):
        url = self.project.web_url_for('project_statistics_redirect')
        res = self.app.get(url, auth=self.auth)
        assert_equal(res.status_code, 302)
        assert_in(self.project.web_url_for('project_statistics', _guid=True), res.location)

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
    def test_get_registrations_sorted_by_registered_date_descending(self):
        # register a project several times, with various registered_dates
        registrations = []
        for days_ago in (21, 3, 2, 8, 13, 5, 1):
            registration = RegistrationFactory(project=self.project)
            reg_date = registration.registered_date - dt.timedelta(days_ago)
            registration.registered_date = reg_date
            registration.save()
            registrations.append(registration)

        registrations.sort(key=lambda r: r.registered_date, reverse=True)
        expected = [ r._id for r in registrations ]

        registrations_url = self.project.api_url_for('get_registrations')
        res = self.app.get(registrations_url, auth=self.auth)
        data = res.json
        actual = [ n['id'] for n in data['nodes'] ]

        assert_equal(actual, expected)



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


class TestChildrenViews(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = AuthUserFactory()

    def test_get_children(self):
        project = ProjectFactory(creator=self.user)
        child = NodeFactory(parent=project, creator=self.user)

        url = project.api_url_for('get_children')
        res = self.app.get(url, auth=self.user.auth)

        nodes = res.json['nodes']
        assert_equal(len(nodes), 1)
        assert_equal(nodes[0]['id'], child._primary_key)

    def test_get_children_includes_pointers(self):
        project = ProjectFactory(creator=self.user)
        pointed = ProjectFactory()
        project.add_pointer(pointed, Auth(self.user))
        project.save()

        url = project.api_url_for('get_children')
        res = self.app.get(url, auth=self.user.auth)

        nodes = res.json['nodes']
        assert_equal(len(nodes), 1)
        assert_equal(nodes[0]['title'], pointed.title)
        pointer = Pointer.find_one(Q('node', 'eq', pointed))
        assert_equal(nodes[0]['id'], pointer._primary_key)

    def test_get_children_filter_for_permissions(self):
        # self.user has admin access to this project
        project = ProjectFactory(creator=self.user)

        # self.user only has read access to this project, which project points
        # to
        read_only_pointed = ProjectFactory()
        read_only_creator = read_only_pointed.creator
        read_only_pointed.add_contributor(self.user, auth=Auth(read_only_creator), permissions=['read'])
        read_only_pointed.save()

        # self.user only has read access to this project, which is a subproject
        # of project
        read_only = ProjectFactory()
        read_only_pointed.add_contributor(self.user, auth=Auth(read_only_creator), permissions=['read'])
        project.nodes.append(read_only)

        # self.user adds a pointer to read_only
        project.add_pointer(read_only_pointed, Auth(self.user))
        project.save()

        url = project.api_url_for('get_children')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['nodes']), 2)

        url = project.api_url_for('get_children', permissions='write')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(len(res.json['nodes']), 0)

    def test_get_children_render_nodes_receives_auth(self):
        project = ProjectFactory(creator=self.user)
        NodeFactory(parent=project, creator=self.user)

        url = project.api_url_for('get_children')
        res = self.app.get(url, auth=self.user.auth)

        perm = res.json['nodes'][0]['permissions']
        assert_equal(perm, 'admin')


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
        child1_id = tree['children'][0]['node']['id']
        child2_id = tree['children'][1]['node']['id']
        child3_id = tree['children'][2]['node']['id']
        assert_equal(parent_node_id, project._primary_key)
        assert_equal(child1_id, child1._primary_key)
        assert_equal(child2_id, child2._primary_key)
        assert_equal(child3_id, child3._primary_key)

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

    def test_sanitization_of_edit_profile(self):
        url = api_url_for('edit_profile', uid=self.user._id)
        post_data = {'name': 'fullname', 'value': 'new<b> name</b>     '}
        request = self.app.post(url, post_data, auth=self.user.auth)
        assert_equal('new name', request.json['name'])

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
        user.emails[0] = user.emails[0].capitalize()
        user.save()
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
        oauth_settings = GitHubAccountFactory()
        oauth_settings.save()
        self.user.external_accounts.append(oauth_settings)
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
        oauth_settings = GitHubAccountFactory()
        oauth_settings.save()
        self.user.external_accounts.append(oauth_settings)
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

    def test_get_current_user_gravatar_default_size(self):
        url = api_url_for('current_user_gravatar')
        res = self.app.get(url, auth=self.user.auth)
        current_user_gravatar = res.json['gravatar_url']
        assert_true(current_user_gravatar is not None)
        url = api_url_for('get_gravatar', uid=self.user._id)
        res = self.app.get(url, auth=self.user.auth)
        my_user_gravatar = res.json['gravatar_url']
        assert_equal(current_user_gravatar, my_user_gravatar)

    def test_get_other_user_gravatar_default_size(self):
        user2 = AuthUserFactory()
        url = api_url_for('current_user_gravatar')
        res = self.app.get(url, auth=self.user.auth)
        current_user_gravatar = res.json['gravatar_url']
        url = api_url_for('get_gravatar', uid=user2._id)
        res = self.app.get(url, auth=self.user.auth)
        user2_gravatar = res.json['gravatar_url']
        assert_true(user2_gravatar is not None)
        assert_not_equal(current_user_gravatar, user2_gravatar)

    def test_get_current_user_gravatar_specific_size(self):
        url = api_url_for('current_user_gravatar')
        res = self.app.get(url, auth=self.user.auth)
        current_user_default_gravatar = res.json['gravatar_url']
        url = api_url_for('current_user_gravatar', size=11)
        res = self.app.get(url, auth=self.user.auth)
        current_user_small_gravatar = res.json['gravatar_url']
        assert_true(current_user_small_gravatar is not None)
        assert_not_equal(current_user_default_gravatar, current_user_small_gravatar)

    def test_get_other_user_gravatar_specific_size(self):
        user2 = AuthUserFactory()
        url = api_url_for('get_gravatar', uid=user2._id)
        res = self.app.get(url, auth=self.user.auth)
        gravatar_default_size = res.json['gravatar_url']
        url = api_url_for('get_gravatar', uid=user2._id, size=11)
        res = self.app.get(url, auth=self.user.auth)
        gravatar_small = res.json['gravatar_url']
        assert_true(gravatar_small is not None)
        assert_not_equal(gravatar_default_size, gravatar_small)

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
        email = fake.email()
        self.user.emails.append(email)
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
        email = fake.email()
        self.user.emails.append(email)
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

    # TODO: Uncomment once outstanding issues with this feature are addressed
    # def test_twitter_redirect_success(self):
    #     self.user.social['twitter'] = fake.last_name()
    #     self.user.save()

    #     res = self.app.get(web_url_for('redirect_to_twitter', twitter_handle=self.user.social['twitter']))
    #     assert_equals(res.status_code, http.FOUND)
    #     assert_in(self.user.url, res.location)

    # def test_twitter_redirect_is_case_insensitive(self):
    #     self.user.social['twitter'] = fake.last_name()
    #     self.user.save()

    #     res1 = self.app.get(web_url_for('redirect_to_twitter', twitter_handle=self.user.social['twitter']))
    #     res2 = self.app.get(web_url_for('redirect_to_twitter', twitter_handle=self.user.social['twitter'].lower()))
    #     assert_equal(res1.location, res2.location)

    # def test_twitter_redirect_unassociated_twitter_handle_returns_404(self):
    #     unassociated_handle = fake.last_name()
    #     expected_error = 'There is no active user associated with the Twitter handle: {0}.'.format(unassociated_handle)

    #     res = self.app.get(
    #         web_url_for('redirect_to_twitter', twitter_handle=unassociated_handle),
    #         expect_errors=True
    #     )
    #     assert_equal(res.status_code, http.NOT_FOUND)
    #     assert_true(expected_error in res.body)

    # def test_twitter_redirect_handle_with_multiple_associated_accounts_redirects_to_selection_page(self):
    #     self.user.social['twitter'] = fake.last_name()
    #     self.user.save()
    #     user2 = AuthUserFactory()
    #     user2.social['twitter'] = self.user.social['twitter']
    #     user2.save()

    #     expected_error = 'There are multiple OSF accounts associated with the Twitter handle: <strong>{0}</strong>.'.format(self.user.social['twitter'])
    #     res = self.app.get(
    #         web_url_for(
    #             'redirect_to_twitter',
    #             twitter_handle=self.user.social['twitter'],
    #             expect_error=True
    #         )
    #     )
    #     assert_equal(res.status_code, http.MULTIPLE_CHOICES)
    #     assert_true(expected_error in res.body)
    #     assert_true(self.user.url in res.body)
    #     assert_true(user2.url in res.body)


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
        self.user.save()

    @mock.patch('website.profile.views.push_status_message')
    def test_password_change_valid(self, mock_push_status_message):
        old_password = 'password'
        new_password = 'Pa$$w0rd'
        confirm_password = new_password
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
            new_password='12345',
            confirm_password='12345',
            error_message='Password should be at least six characters',
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
        name, email = fake.name(), fake.email()
        res = serialize_unregistered(fullname=name, email=email)
        assert_equal(res['fullname'], name)
        assert_equal(res['email'], email)
        assert_equal(res['id'], None)
        assert_false(res['registered'])
        assert_true(res['gravatar'])
        assert_false(res['active'])

    def test_deserialize_contributors(self):
        contrib = UserFactory()
        unreg = UnregUserFactory()
        name, email = fake.name(), fake.email()
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
        email = fake.email()
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

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_deserialize_contributors_sends_unreg_contributor_added_signal(self, _):
        unreg = UnregUserFactory()
        from website.project.signals import unreg_contributor_added
        serialized = [serialize_unregistered(fake.name(), unreg.username)]
        serialized[0]['visible'] = True
        with capture_signals() as mock_signals:
            deserialize_contributors(self.project, serialized,
                                     auth=Auth(self.creator))
        assert_equal(mock_signals.signals_sent(), set([unreg_contributor_added]))

    def test_serialize_unregistered_with_record(self):
        name, email = fake.name(), fake.email()
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
        assert_true(res['gravatar_url'])
        assert_equal(res['fullname'], name)
        assert_equal(res['email'], email)

    def test_add_contributor_with_unreg_contribs_and_reg_contribs(self):
        n_contributors_pre = len(self.project.contributors)
        reg_user = UserFactory()
        name, email = fake.name(), fake.email()
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
        self.project.nodes.append(comp1)
        self.project.nodes.append(comp2)
        self.project.save()

        # An unreg user is added to the project AND its components
        unreg_user = {  # dict because user has not previous unreg record
            'id': None,
            'registered': False,
            'fullname': fake.name(),
            'email': fake.email(),
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
        name, email = fake.name(), fake.email()
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
        project = ProjectFactory()
        project.add_contributors(contributors, auth=self.auth)
        project.save()
        assert_true(send_mail.called)
        send_mail.assert_called_with(
            contributor.username,
            mails.CONTRIBUTOR_ADDED,
            user=contributor,
            node=project,
            referrer_name=self.auth.user.fullname)
        assert_almost_equal(contributor.contributor_added_email_records[project._id]['last_sent'], int(time.time()), delta=1)

    @mock.patch('website.mails.send_mail')
    def test_contributor_added_email_not_sent_to_unreg_user(self, send_mail):
        unreg_user = UnregUserFactory()
        contributors = [{
            'user': unreg_user,
            'visible': True,
            'permissions': ['read', 'write']
        }]
        project = ProjectFactory()
        project.add_contributors(contributors, auth=Auth(self.project.creator))
        project.save()
        assert_false(send_mail.called)

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

    def test_add_multiple_contributors_only_adds_one_log(self):
        n_logs_pre = len(self.project.logs)
        reg_user = UserFactory()
        name = fake.name()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': fake.email(),
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
        assert_equal(len(self.project.logs), n_logs_pre + 1)

    def test_add_contribs_to_multiple_nodes(self):
        child = NodeFactory(parent=self.project, creator=self.creator)
        n_contributors_pre = len(child.contributors)
        reg_user = UserFactory()
        name, email = fake.name(), fake.email()
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
        url = "/api/v1/project/{0}/contributors/".format(self.project._id)
        self.app.post_json(url, payload).maybe_follow()
        child.reload()
        assert_equal(len(child.contributors),
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
        name, email = fake.name(), fake.email()
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
        name, email = fake.name(), fake.email()
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
            fullname=fake.name(), email=fake.email(),
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
        given_email = fake.email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        send_claim_email(email=given_email, user=unreg_user, node=project)

        assert_true(send_mail.called)
        assert_true(send_mail.called_with(
            to_addr=given_email,
            mail=mails.INVITE
        ))

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_to_referrer(self, send_mail):
        project = ProjectFactory()
        referrer = project.creator
        given_email, real_email = fake.email(), fake.email()
        unreg_user = project.add_unregistered_contributor(fullname=fake.name(),
                                                          email=given_email, auth=Auth(
                                                              referrer)
                                                          )
        project.save()
        send_claim_email(email=real_email, user=unreg_user, node=project)

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
            node=project
        )

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_send_claim_email_before_throttle_expires(self, send_mail):
        project = ProjectFactory()
        given_email = fake.email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        send_claim_email(email=fake.email(), user=unreg_user, node=project)
        send_mail.reset_mock()
        # 2nd call raises error because throttle hasn't expired
        with assert_raises(HTTPError):
            send_claim_email(email=fake.email(), user=unreg_user, node=project)
        assert_false(send_mail.called)


class TestClaimViews(OsfTestCase):

    def setUp(self):
        super(TestClaimViews, self).setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        self.given_name = fake.name()
        self.given_email = fake.email()
        self.user = self.project.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

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
            unreg_user=self.user,
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
            unreg_user=self.user,
            node=self.project,
        )
        mock_send_mail.reset_mock()
        # second call raises error because it was called before throttle period
        with assert_raises(HTTPError):
            send_claim_registered_email(
                claimer=reg_user,
                unreg_user=self.user,
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

    def test_invalid_claim_form_redirects_to_register_page(self):
        uid = self.user._primary_key
        pid = self.project._primary_key
        url = '/user/{uid}/{pid}/claim/?token=badtoken'.format(**locals())
        res = self.app.get(url, expect_errors=True).maybe_follow()
        assert_equal(res.status_code, 200)
        assert_equal(res.request.path, web_url_for('auth_login'))

    def test_posting_to_claim_form_with_valid_data(self):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, {
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        }).maybe_follow()
        assert_equal(res.status_code, 200)
        self.user.reload()
        assert_true(self.user.is_registered)
        assert_true(self.user.is_active)
        assert_not_in(self.project._primary_key, self.user.unclaimed_records)

    def test_posting_to_claim_form_removes_all_unclaimed_data(self):
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

    def test_posting_to_claim_form_sets_fullname_to_given_name(self):
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
        email = fake.email()  # email that is different from the one the referrer gave
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


class TestWatchViews(OsfTestCase):

    def setUp(self):
        super(TestWatchViews, self).setUp()
        self.user = AuthUserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.auth = self.user.auth  # used for requests auth
        # A public project
        self.project = ProjectFactory(is_public=True)
        self.project.save()
        # Manually reset log date to 100 days ago so it won't show up in feed
        self.project.logs[0].date = dt.datetime.utcnow() - dt.timedelta(days=100)
        self.project.logs[0].save()
        # A log added now
        self.last_log = self.project.add_log(
            NodeLog.TAG_ADDED,
            params={'node': self.project._primary_key},
            auth=self.consolidate_auth,
            log_date=dt.datetime.utcnow(),
            save=True,
        )
        # Clear watched list
        self.user.watched = []
        self.user.save()

    def test_watching_a_project_appends_to_users_watched_list(self):
        n_watched_then = len(self.user.watched)
        url = '/api/v1/project/{0}/watch/'.format(self.project._id)
        res = self.app.post_json(url,
                                 params={"digest": True},
                                 auth=self.auth)
        assert_equal(res.json['watchCount'], 1)
        self.user.reload()
        n_watched_now = len(self.user.watched)
        assert_equal(res.status_code, 200)
        assert_equal(n_watched_now, n_watched_then + 1)
        assert_true(self.user.watched[-1].digest)

    def test_watching_project_twice_returns_400(self):
        url = "/api/v1/project/{0}/watch/".format(self.project._id)
        res = self.app.post_json(url,
                                 params={},
                                 auth=self.auth)
        assert_equal(res.status_code, 200)
        # User tries to watch a node she's already watching
        res2 = self.app.post_json(url,
                                  params={},
                                  auth=self.auth,
                                  expect_errors=True)
        assert_equal(res2.status_code, http.BAD_REQUEST)

    def test_unwatching_a_project_removes_from_watched_list(self):
        # The user has already watched a project
        watch_config = WatchConfigFactory(node=self.project)
        self.user.watch(watch_config)
        self.user.save()
        n_watched_then = len(self.user.watched)
        url = '/api/v1/project/{0}/unwatch/'.format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.user.reload()
        n_watched_now = len(self.user.watched)
        assert_equal(res.status_code, 200)
        assert_equal(n_watched_now, n_watched_then - 1)
        assert_false(self.user.is_watching(self.project))

    def test_toggle_watch(self):
        # The user is not watching project
        assert_false(self.user.is_watching(self.project))
        url = "/api/v1/project/{0}/togglewatch/".format(self.project._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        # The response json has a watchcount and watched property
        assert_equal(res.json['watchCount'], 1)
        assert_true(res.json['watched'])
        assert_equal(res.status_code, 200)
        self.user.reload()
        # The user is now watching the project
        assert_true(res.json['watched'])
        assert_true(self.user.is_watching(self.project))

    def test_toggle_watch_node(self):
        # The project has a public sub-node
        node = NodeFactory(creator=self.user, parent=self.project, is_public=True)
        url = "/api/v1/project/{}/node/{}/togglewatch/".format(self.project._id,
                                                               node._id)
        res = self.app.post_json(url, {}, auth=self.auth)
        assert_equal(res.status_code, 200)
        self.user.reload()
        # The user is now watching the sub-node
        assert_true(res.json['watched'])
        assert_true(self.user.is_watching(node))

    def test_get_watched_logs(self):
        project = ProjectFactory()
        # Add some logs
        for _ in range(12):
            project.add_log('file_added', params={'node': project._id}, auth=self.consolidate_auth)

        project.save()
        watch_cfg = WatchConfigFactory(node=project)
        self.user.watch(watch_cfg)
        self.user.save()
        url = api_url_for("watched_logs_get")
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), 10)
        # 1 project create log then 12 generated logs
        assert_equal(res.json['total'], 12 + 1)
        assert_equal(res.json['page'], 0)
        assert_equal(res.json['pages'], 2)
        assert_equal(res.json['logs'][0]['action'], 'file_added')

    def test_get_more_watched_logs(self):
        project = ProjectFactory()
        # Add some logs
        for _ in range(12):
            project.add_log('file_added', params={'node': project._id}, auth=self.consolidate_auth)

        project.save()
        watch_cfg = WatchConfigFactory(node=project)
        self.user.watch(watch_cfg)
        self.user.save()
        url = api_url_for("watched_logs_get")
        page = 1
        res = self.app.get(url, {'page': page}, auth=self.auth)
        assert_equal(len(res.json['logs']), 3)
        # 1 project create log then 12 generated logs
        assert_equal(res.json['total'], 12 + 1)
        assert_equal(res.json['page'], page)
        assert_equal(res.json['pages'], 2)
        assert_equal(res.json['logs'][0]['action'], 'file_added')

    def test_get_more_watched_logs_invalid_page(self):
        project = ProjectFactory()
        watch_cfg = WatchConfigFactory(node=project)
        self.user.watch(watch_cfg)
        self.user.save()
        url = api_url_for("watched_logs_get")
        invalid_page = 'invalid page'
        res = self.app.get(
            url, {'page': invalid_page}, auth=self.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)
        assert_equal(
            res.json['message_long'],
            'Invalid value for "page".'
        )

    def test_get_more_watched_logs_invalid_size(self):
        project = ProjectFactory()
        watch_cfg = WatchConfigFactory(node=project)
        self.user.watch(watch_cfg)
        self.user.save()
        url = api_url_for("watched_logs_get")
        invalid_size = 'invalid size'
        res = self.app.get(
            url, {'size': invalid_size}, auth=self.auth, expect_errors=True
        )
        assert_equal(res.status_code, 400)
        assert_equal(
            res.json['message_long'],
            'Invalid value for "size".'
        )

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

        has_controls = res.lxml.xpath('//li[@node_reference]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
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
            '//li[@node_reference]//i[contains(@class, "remove-pointer")]')
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

        pointer_nodes = res.lxml.xpath('//li[@node_reference]')
        has_controls = res.lxml.xpath('//li[@node_reference]/p[starts-with(normalize-space(text()), "Private Link")]//i[contains(@class, "remove-pointer")]')
        assert_equal(len(pointer_nodes), 1)
        assert_false(has_controls)

    def test_pointer_list_read_contributor_cannot_remove_public_component_entry(self):
        url = web_url_for('view_project', pid=self.project._id)

        self.project.add_pointer(ProjectFactory(creator=self.user),
                                 auth=Auth(user=self.user))

        user2 = AuthUserFactory()
        self.project.add_contributor(user2,
                                     auth=Auth(self.project.creator),
                                     permissions=[permissions.READ])
        self.project.save()

        res = self.app.get(url, auth=user2.auth).maybe_follow()
        assert_equal(res.status_code, 200)

        pointer_nodes = res.lxml.xpath('//li[@node_reference]')
        has_controls = res.lxml.xpath(
            '//li[@node_reference]//i[contains(@class, "remove-pointer")]')
        assert_equal(len(pointer_nodes), 1)
        assert_equal(len(has_controls), 0)

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/1109
    def test_get_pointed_excludes_folders(self):
        pointer_project = ProjectFactory(is_public=True)  # project that points to another project
        pointed_project = ProjectFactory(creator=self.user)  # project that other project points to
        pointer_project.add_pointer(pointed_project, Auth(pointer_project.creator), save=True)

        # Project is in an organizer collection
        collection = CollectionFactory(creator=pointed_project.creator)
        collection.add_pointer(pointed_project, Auth(pointed_project.creator), save=True)

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
            len(self.project.nodes),
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
            len(self.project.nodes),
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
            len(self.project.nodes),
            5
        )

    def test_add_pointers_not_provided(self):
        url = self.project.api_url + 'pointer/'
        res = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_move_pointers(self):
        project_two = ProjectFactory(creator=self.user)
        url = api_url_for('move_pointers')
        node = NodeFactory()
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)

        assert_equal(len(self.project.nodes), 1)
        assert_equal(len(project_two.nodes), 0)

        user_auth = self.user.auth
        move_request = \
            {
                'fromNodeId': self.project._id,
                'toNodeId': project_two._id,
                'pointerIds': [pointer.node._id],
            }
        self.app.post_json(
            url,
            move_request,
            auth=user_auth,
        ).maybe_follow()
        self.project.reload()
        project_two.reload()
        assert_equal(len(self.project.nodes), 0)
        assert_equal(len(project_two.nodes), 1)

    def test_remove_pointer(self):
        url = self.project.api_url + 'pointer/'
        node = NodeFactory()
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)
        self.app.delete_json(
            url,
            {'pointerId': pointer._id},
            auth=self.user.auth,
        )
        self.project.reload()
        assert_equal(
            len(self.project.nodes),
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
        node = NodeFactory()
        pointer = Pointer(node=node)
        res = self.app.delete_json(
            url,
            {'pointerId': pointer._id},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_fork_pointer(self):
        url = self.project.api_url + 'pointer/fork/'
        node = NodeFactory(creator=self.user)
        pointer = self.project.add_pointer(node, auth=self.consolidate_auth)
        self.app.post_json(
            url,
            {'pointerId': pointer._id},
            auth=self.user.auth
        )

    def test_fork_pointer_not_provided(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post_json(url, {}, auth=self.user.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, 400)

    def test_fork_pointer_not_found(self):
        url = self.project.api_url + 'pointer/fork/'
        res = self.app.post_json(
            url,
            {'pointerId': None},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_fork_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/fork/'
        node = NodeFactory()
        pointer = Pointer(node=node)
        res = self.app.post_json(
            url,
            {'pointerId': pointer._id},
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, 400)

    def test_before_register_with_pointer(self):
        "Assert that link warning appears in before register callback."
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


class TestPublicViews(OsfTestCase):

    def test_explore(self):
        res = self.app.get("/explore/").maybe_follow()
        assert_equal(res.status_code, 200)

    def test_forgot_password_get(self):
        res = self.app.get(web_url_for('forgot_password_get'))
        assert_equal(res.status_code, 200)
        assert_in('Forgot Password', res.body)


class TestAuthViews(OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    def test_merge_user(self):
        dupe = UserFactory(
            username="copy@cat.com",
            emails=['copy@cat.com']
        )
        dupe.set_password("copycat")
        dupe.save()
        url = "/api/v1/user/merge/"
        self.app.post_json(
            url,
            {
                "merged_username": "copy@cat.com",
                "merged_password": "copycat"
            },
            auth=self.auth,
        )
        self.user.reload()
        dupe.reload()
        assert_true(dupe.is_merged)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_sends_confirm_email(self, send_mail):
        url = '/register/'
        self.app.post(url, {
            'register-fullname': 'Freddie Mercury',
            'register-username': 'fred@queen.com',
            'register-password': 'killerqueen',
            'register-username2': 'fred@queen.com',
            'register-password2': 'killerqueen',
        })
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(
            to_addr='fred@queen.com'
        ))

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_ok(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake.email(), 'underpressure'
        self.app.post_json(
            url,
            {
                'fullName': name,
                'email1': email,
                'email2': email,
                'password': password,
            }
        )
        user = User.find_one(Q('username', 'eq', email))
        assert_equal(user.fullname, name)

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2902
    @mock.patch('framework.auth.views.mails.send_mail')
    def test_register_email_case_insensitive(self, _):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake.email(), 'underpressure'
        self.app.post_json(
            url,
            {
                'fullName': name,
                'email1': email,
                'email2': str(email).upper(),
                'password': password,
            }
        )
        user = User.find_one(Q('username', 'eq', email))
        assert_equal(user.fullname, name)

    @mock.patch('framework.auth.views.send_confirm_email')
    def test_register_scrubs_username(self, _):
        url = api_url_for('register_user')
        name = "<i>Eunice</i> O' \"Cornwallis\"<script type='text/javascript' src='http://www.cornify.com/js/cornify.js'></script><script type='text/javascript'>cornify_add()</script>"
        email, password = fake.email(), 'underpressure'
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
        user = User.find_one(Q('username', 'eq', email))

        assert_equal(res.status_code, http.OK)
        assert_equal(user.fullname, expected_scrub_username)

    def test_register_email_mismatch(self):
        url = api_url_for('register_user')
        name, email, password = fake.name(), fake.email(), 'underpressure'
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
        users = User.find(Q('username', 'eq', email))
        assert_equal(users.count(), 0)

    def test_register_after_being_invited_as_unreg_contributor(self):
        # Regression test for:
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/861
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/1021
        #    https://github.com/CenterForOpenScience/openscienceframework.org/issues/1026
        # A user is invited as an unregistered contributor
        project = ProjectFactory()

        name, email = fake.name(), fake.email()

        project.add_unregistered_contributor(fullname=name, email=email, auth=Auth(project.creator))
        project.save()

        # The new, unregistered user
        new_user = User.find_one(Q('username', 'eq', email))

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
        name, email, password = fake.name(), fake.email(), 'underpressure'
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

    @mock.patch('framework.auth.views.send_confirm_email')
    def test_register_post_sends_user_registered_signal(self, mock_send_confirm_email):
        url = web_url_for('auth_register_post')
        name, email, password = fake.name(), fake.email(), 'underpressure'
        with capture_signals() as mock_signals:
            self.app.post(url, {
                'register-fullname': name,
                'register-username': email,
                'register-password': password,
                'register-username2': email,
                'register-password2': password
            })
        assert_equal(mock_signals.signals_sent(), set([auth.signals.user_registered,
                                                       auth.signals.unconfirmed_user_created]))
        assert_true(mock_send_confirm_email.called)

    def test_resend_confirmation_get(self):
        res = self.app.get('/resend/')
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation(self, send_mail):
        email = 'test@example.com'
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
        email = 'test@example.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token, self.user.username)
        res = self.app.get(url)
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], True)
        assert_equal(res.status_code, 302)
        login_url = '/login/?existing_user={}'.format(urllib.quote_plus(self.user.username))
        assert_in(login_url, res.body)

    def test_get_email_to_add_no_email(self):
        email_verifications = self.user.get_unconfirmed_emails
        assert_equal(email_verifications, [])

    def test_get_unconfirmed_email(self):
        email = 'test@example.com'
        self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        email_verifications = self.user.get_unconfirmed_emails
        assert_equal(email_verifications, [])

    def test_get_email_to_add(self):
        email = 'test@example.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token, self.user.username)
        self.app.get(url)
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], True)
        email_verifications = self.user.get_unconfirmed_emails
        assert_equal(email_verifications[0]['address'], 'test@example.com')

    def test_add_email(self):
        email = 'test@example.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token)
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.get_unconfirmed_emails
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put_json(put_email_url, email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert_equal(res.json_body['status'], 'success')
        assert_equal(self.user.emails[1], 'test@example.com')

    def test_remove_email(self):
        email = 'test@example.com'
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token)
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.get_unconfirmed_emails
        remove_email_url = api_url_for('unconfirmed_email_remove')
        remove_res = self.app.delete_json(remove_email_url, email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert_equal(remove_res.json_body['status'], 'success')
        assert_equal(self.user.get_unconfirmed_emails, [])

    def test_add_expired_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = 'test@example.com'
        token = self.user.add_unconfirmed_email(email)
        dt.datetime.utcnow() - dt.timedelta(days=100)
        self.user.email_verifications[token]['expiration'] = dt.datetime.utcnow() - dt.timedelta(days=100)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['email'], email)
        self.user.clean_email_verifications()
        unconfirmed_emails = self.user.get_unconfirmed_emails
        assert_equal(unconfirmed_emails, [])
        assert_equal(self.user.email_verifications, {})

    def test_add_invalid_email(self):
        # Do not return expired token and removes it from user.email_verifications
        email = u'\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello@yourmom.com'
        # illegal_str = u'\u0000\u0008\u000b\u000c\u000e\u001f\ufffe\uffffHello'
        # illegal_str += unichr(0xd800) + unichr(0xdbff) + ' World'
        # email = 'test@example.com'
        with assert_raises(ValidationError):
            self.user.add_unconfirmed_email(email)

    def test_add_email_merge(self):
        email = "copy@cat.com"
        dupe = UserFactory(
            username=email,
            emails=[email]
        )
        dupe.save()
        token = self.user.add_unconfirmed_email(email)
        self.user.save()
        self.user.reload()
        assert_equal(self.user.email_verifications[token]['confirmed'], False)
        url = '/confirm/{}/{}/?logout=1'.format(self.user._id, token)
        self.app.get(url)
        self.user.reload()
        email_verifications = self.user.get_unconfirmed_emails
        put_email_url = api_url_for('unconfirmed_email_add')
        res = self.app.put_json(put_email_url, email_verifications[0], auth=self.user.auth)
        self.user.reload()
        assert_equal(res.json_body['status'], 'success')
        assert_equal(self.user.emails[1], 'copy@cat.com')

    def test_resend_confirmation_without_user_id(self):
        email = 'test@example.com'
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
        email = 'test@example.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': True, 'confirmed': False}
        res = self.app.put_json(url, {'id': self.user._id, 'email': header}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Cannnot resend confirmation for confirmed emails')

    def test_resend_confirmation_not_work_for_confirmed_email(self):
        email = 'test@example.com'
        url = api_url_for('resend_confirmation')
        header = {'address': email, 'primary': False, 'confirmed': True}
        res = self.app.put_json(url, {'id': self.user._id, 'email': header}, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['message_long'], 'Cannnot resend confirmation for confirmed emails')

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_does_not_send_before_throttle_expires(self, send_mail):
        email = 'test@example.com'
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
        user = User.create_unconfirmed('brian@queen.com', 'bicycle123', 'Brian May')
        assert_false(user.is_registered)  # sanity check
        user.save()
        confirmation_url = user.get_confirmation_url('brian@queen.com', external=False)
        res = self.app.get(confirmation_url)
        assert_equal(res.status_code, 302, 'redirects to settings page')
        res = res.follow()
        user.reload()
        assert_true(user.is_registered)


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
        self.project = ProjectFactory.build(creator=self.user, is_public=True)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_files_get(self):
        url = self.project.api_url_for('collect_file_trees')
        res = self.app.get(url, auth=self.user.auth)
        expected = _view_project(self.project, auth=Auth(user=self.user))

        assert_equal(res.status_code, http.OK)
        assert_equal(res.json['node'], expected['node'])
        assert_in('tree_js', res.json)
        assert_in('tree_css', res.json)

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


@requires_search
class TestSearchViews(OsfTestCase):

    def setUp(self):
        super(TestSearchViews, self).setUp()
        import website.search.search as search
        search.delete_all()

        self.project = ProjectFactory(creator=UserFactory(fullname='Robbie Williams'))
        self.contrib = UserFactory(fullname='Brian May')
        for i in range(0, 12):
            UserFactory(fullname='Freddie Mercury{}'.format(i))

    def tearDown(self):
        super(TestSearchViews, self).tearDown()
        import website.search.search as search
        search.delete_all()

    def test_search_contributor(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': self.contrib.fullname})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        assert_equal(len(result), 1)
        brian = result[0]
        assert_equal(brian['fullname'], self.contrib.fullname)
        assert_in('gravatar_url', brian)
        assert_equal(brian['registered'], self.contrib.is_registered)
        assert_equal(brian['active'], self.contrib.is_active)

    def test_search_pagination_default(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr'})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(pages, 3)
        assert_equal(page, 0)

    def test_search_pagination_default_page_1(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'page': 1})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 1)

    def test_search_pagination_default_page_2(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'page': 2})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 2)
        assert_equal(page, 2)

    def test_search_pagination_smaller_pages(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'size': 5})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 0)
        assert_equal(pages, 3)

    def test_search_pagination_smaller_pages_page_2(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'page': 2, 'size': 5, })
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 2)
        assert_equal(page, 2)
        assert_equal(pages, 3)

    def test_search_projects(self):
        url = '/search/'
        res = self.app.get(url, {'q': self.project.title})
        assert_equal(res.status_code, 200)


class TestODMTitleSearch(OsfTestCase):
    """ Docs from original method:
    :arg term: The substring of the title.
    :arg category: Category of the node.
    :arg isDeleted: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg isFolder: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg isRegistration: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg includePublic: yes or no. Whether the projects listed should include public projects.
    :arg includeContributed: yes or no. Whether the search should include projects the current user has
        contributed to.
    :arg ignoreNode: a list of nodes that should not be included in the search.
    :return: a list of dictionaries of projects
    """
    def setUp(self):
        super(TestODMTitleSearch, self).setUp()

        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, title="foo")
        self.project_two = ProjectFactory(creator=self.user_two, title="bar")
        self.public_project = ProjectFactory(creator=self.user_two, is_public=True, title="baz")
        self.registration_project = RegistrationFactory(creator=self.user, title="qux")
        self.folder = CollectionFactory(creator=self.user, title="quux")
        self.dashboard = BookmarkCollectionFactory(creator=self.user, title="Dashboard")
        self.url = api_url_for('search_projects_by_title')

    def test_search_projects_by_title(self):
        res = self.app.get(self.url, {'term': self.project.title}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.public_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.project.title,
                               'includePublic': 'no',
                               'includeContributed': 'yes'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.project.title,
                               'includePublic': 'no',
                               'includeContributed': 'yes',
                               'isRegistration': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.public_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.registration_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 2)
        res = self.app.get(self.url,
                           {
                               'term': self.registration_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.folder.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'yes'
                           }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        res = self.app.get(self.url,
                           {
                               'term': self.folder.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 0)
        res = self.app.get(self.url,
                           {
                               'term': self.dashboard.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 0)
        res = self.app.get(self.url,
                           {
                               'term': self.dashboard.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'yes'
                           }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)


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
        self.project.nodes.append(self.public_component)
        self.project.nodes.append(self.private_component)

        self.project.save()

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_reorder_components_with_private_component(self):

        # contrib tries to reorder components
        payload = {
            'new_list': [
                '{0}:node'.format(self.private_component._primary_key),
                '{0}:node'.format(self.public_component._primary_key),
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
        assert_true(_should_show_wiki_widget(self.project, self.project.creator))
        assert_true(_should_show_wiki_widget(self.project2, self.project.creator))

    def test_show_wiki_is_false_for_read_contributors_when_no_wiki_or_content(self):
        assert_false(_should_show_wiki_widget(self.project, self.read_only_contrib))
        assert_false(_should_show_wiki_widget(self.project2, self.read_only_contrib))

    def test_show_wiki_is_false_for_noncontributors_when_no_wiki_or_content(self):
        assert_false(_should_show_wiki_widget(self.project, self.noncontributor))
        assert_false(_should_show_wiki_widget(self.project2, self.read_only_contrib))


class TestForkViews(OsfTestCase):

    def setUp(self):
        super(TestForkViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory.build(creator=self.user, is_public=True)
        self.consolidated_auth = Auth(user=self.project.creator)
        self.user.save()
        self.project.save()

    def test_fork_private_project_non_contributor(self):
        self.project.set_privacy("private")
        self.project.save()

        url = self.project.api_url_for('node_fork_page')
        non_contributor = AuthUserFactory()
        res = self.app.post_json(url,
                                 auth=non_contributor.auth,
                                 expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_fork_public_project_non_contributor(self):
        url = self.project.api_url_for('node_fork_page')
        non_contributor = AuthUserFactory()
        res = self.app.post_json(url, auth=non_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_fork_project_contributor(self):
        contributor = AuthUserFactory()
        self.project.set_privacy("private")
        self.project.add_contributor(contributor)
        self.project.save()

        url = self.project.api_url_for('node_fork_page')
        res = self.app.post_json(url, auth=contributor.auth)
        assert_equal(res.status_code, 200)

    def test_registered_forks_dont_show_in_fork_list(self):
        fork = self.project.fork_node(self.consolidated_auth)
        RegistrationFactory(project=fork)

        url = self.project.api_url_for('get_forks')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(len(res.json['nodes']), 1)
        assert_equal(res.json['nodes'][0]['id'], fork._id)


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
        node = Node.load(res.json['projectUrl'].replace('/', ''))
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
        node = Node.load(res.json['projectUrl'].replace('/', ''))
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
        node = Node.load(res.json['projectUrl'].replace('/', ''))
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
        node = Node.load(res.json['projectUrl'].replace('/', ''))
        assert_true(node)
        assert_true(node.template_node, other_node)

    def test_project_before_template_no_addons(self):
        project = ProjectFactory()
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert_equal(res.json['prompts'], [])

    def test_project_before_template_with_addons(self):
        project = ProjectWithAddonFactory(addon='github')
        res = self.app.get(project.api_url_for('project_before_template'), auth=project.creator.auth)
        assert_in('GitHub', res.json['prompts'])

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
        res = self.app.get(url)
        assert_equal(res.status_code, 200)


class TestProfileNodeList(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = AuthUserFactory()

        self.public = ProjectFactory(is_public=True)
        self.public_component = NodeFactory(parent=self.public, is_public=True)
        self.private = ProjectFactory(is_public=False)
        self.deleted = ProjectFactory(is_public=True, is_deleted=True)

        for node in (self.public, self.public_component, self.private, self.deleted):
            node.add_contributor(self.user, auth=Auth(node.creator))
            node.save()

    def test_get_public_projects(self):
        url = api_url_for('get_public_projects', uid=self.user._id)
        res = self.app.get(url)
        node_ids = [each['id'] for each in res.json['nodes']]
        assert_in(self.public._id, node_ids)
        assert_not_in(self.private._id, node_ids)
        assert_not_in(self.deleted._id, node_ids)
        assert_not_in(self.public_component._id, node_ids)

    def test_get_public_components(self):
        url = api_url_for('get_public_components', uid=self.user._id)
        res = self.app.get(url)
        node_ids = [each['id'] for each in res.json['nodes']]
        assert_in(self.public_component._id, node_ids)
        assert_not_in(self.public._id, node_ids)
        assert_not_in(self.private._id, node_ids)
        assert_not_in(self.deleted._id, node_ids)

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


class TestUserConfirmSignal(OsfTestCase):

    def test_confirm_user_signal_called_when_user_claims_account(self):
        unclaimed_user = UnconfirmedUserFactory()
        # unclaimed user has been invited to a project.
        referrer = UserFactory()
        project = ProjectFactory(creator=referrer)
        unclaimed_user.add_unclaimed_record(project, referrer, 'foo')
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

if __name__ == '__main__':
    unittest.main()
