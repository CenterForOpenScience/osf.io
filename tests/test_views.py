#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Views tests for the OSF.'''
from __future__ import absolute_import
import unittest
import json
import datetime as dt
import mock
import httplib as http



from nose.tools import *  # PEP8 asserts
from tests.test_features import requires_search
from webtest_plus import TestApp
from webtest.app import AppError
from werkzeug.wrappers import Response

from modularodm import Q

from framework import auth
from framework.exceptions import HTTPError
from framework.auth import User, Auth
from framework.auth.utils import impute_names_model

import website.app
from website.models import Node, Pointer, NodeLog
from website.project.model import ensure_schemas
from website.project.views.contributor import (
    send_claim_email,
    deserialize_contributors
)
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.util import api_url_for, web_url_for
from website import settings, mails
from website.util import rubeus
from website.project.views.node import _view_project
from website.project.views.comment import serialize_comment
from website.project.decorators import choose_key, check_can_access

from tests.base import OsfTestCase, fake, capture_signals, URLLookup, assert_is_redirect
from tests.factories import (
    UserFactory, ApiKeyFactory, ProjectFactory, WatchConfigFactory,
    NodeFactory, NodeLogFactory, AuthUserFactory, UnregUserFactory,
    CommentFactory, PrivateLinkFactory
)


app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings',
)

lookup = URLLookup(app)


class TestViewingProjectWithPrivateLink(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)

        self.user = AuthUserFactory()  # Is NOT a contributor
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory()
        self.link.nodes.append(self.project)
        self.link.save()

        self.project_url = lookup('web', 'view_project', pid=self.project._primary_key)

    def test_has_private_link_key(self):
        res = self.app.get(self.project_url,{'view_only': self.link.key})
        assert_equal(res.status_code, 200)

    def test_not_logged_in_no_key(self):
        res = self.app.get(self.project_url, {'view_only': None})
        assert_is_redirect(res)
        res = res.follow()
        assert_equal(res.request.path, lookup('web', 'auth_login'))

    def test_logged_in_no_private_key(self):
        res = self.app.get(self.project_url, {'view_only': None}, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)


    def test_logged_in_has_key(self):
        res = self.app.get(self.project_url, {'view_only': self.link.key}, auth=self.user.auth)
        assert_equal(res.status_code, 200)

    def test_logged_in_has_key_ring(self):
        self.user.private_links.append(self.link)
        self.user.save()
        #check if key_ring works
        res = self.app.get(self.project_url, {'view_only': None}, auth=self.user.auth)
        assert_is_redirect(res)
        redirected = res.follow()
        assert_equal(redirected.request.GET['view_only'], self.link.key)
        assert_equal(redirected.status_code, 200)

    def test_logged_in_with_no_key_ring(self):
        #check if key_ring works
        res = self.app.get(self.project_url, {'view_only': None}, auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_logged_in_with_private_key_with_key_ring(self):
        self.user.private_links.append(self.link)
        self.user.save()
        #check if key_ring works
        link2 = PrivateLinkFactory(key="123456")
        res = self.app.get(self.project_url, {'view_only': link2.key}, auth=self.user.auth)
        assert_equal(res.request.GET['view_only'], link2.key)
        assert_equal(res.status_code, 302)
        res2 = res.maybe_follow(auth=self.user.auth)
        assert_equal(res2.request.GET['view_only'], self.link.key)
        assert_equal(res2.status_code, 200)

    @unittest.skip('Skipping for now until we find a way to mock/set the referrer')
    def test_prepare_private_key(self):
        res = self.app.get(self.project_url, {'key': self.link.key})

        res = res.click('Registrations')

        assert_is_redirect(res)
        res = res.follow()

        assert_equal(res.status_code, 200)
        assert_equal(res.request.GET['key'], self.link.key)

    def test_choose_key(self):
        # User is not logged in, goes to route with a private key
        res = choose_key(
            key=self.link.key,
            key_ring=set(),
            api_node='doesntmatter',
            node=self.project,
            auth=Auth(None)
        )
        assert_is(res, None)

    def test_choose_key_form_key_ring(self):
        with app.test_request_context():
            res = choose_key('nope', key_ring=set([self.link.key]), node=self.project,
                auth=Auth(None))
        assert_true(isinstance(res, Response))

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
        ensure_schemas()
        self.app = TestApp(app)
        self.user1 = UserFactory.build()
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user1.api_keys.append(api_key)
        self.user1.save()
        self.consolidate_auth1 = Auth(user=self.user1, api_key=api_key)
        self.auth = ('test', api_key._primary_key)
        self.user2 = UserFactory()
        # A project has 2 contributors
        self.project = ProjectFactory(
            title="Ham",
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user1)
        self.project.add_contributor(self.user2)
        self.project.api_keys.append(api_key)
        self.project.save()

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
        assert_equal(data['node']['logs'][-1]['action'], 'project_created')
        assert_equal(data['node']['children_ids'],
                        [str(n._primary_key) for n in self.project.nodes])
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
                    {'id': self.project.creator._id, 'permission': 'admin', 'registered': True, 'visible': True},
                    {'id': self.user1._id, 'permission': 'read', 'registered': True, 'visible': True},
                    {'id': self.user2._id, 'permission': 'admin', 'registered': True, 'visible': True},
                ]
            },
            auth=self.auth,
        )

        self.project.reload()

        assert_equal(self.project.get_permissions(self.user1), ['read'])
        assert_equal(self.project.get_permissions(self.user2), ['read', 'write', 'admin'])

    def test_contributor_manage_reorder(self):

        # Two users are added as a contributor via a POST request
        project = ProjectFactory(creator=self.user1, is_public=True)
        reg_user1, reg_user2 = UserFactory(), UserFactory()
        project.add_contributors(
            [
                {'user': reg_user1, 'permissions': ['read', 'write', 'admin'], 'visible': True},
                {'user': reg_user2, 'permissions': ['read', 'write', 'admin'], 'visible': False},
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
                    {'id': reg_user2._id, 'permission': 'admin', 'registered': True, 'visible': False},
                    {'id': project.creator._id, 'permission': 'admin', 'registered': True, 'visible': True},
                    {'id': unregistered_user._id, 'permission': 'admin', 'registered': False, 'visible': True},
                    {'id': reg_user1._id, 'permission': 'admin', 'registered': True, 'visible': True},
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
        url = "/api/v1/project/{0}/removecontributors/".format(self.project._id)
        # User 1 removes user2
        res = self.app.post(url, json.dumps({"id": self.user2._id}),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        self.project.reload()
        assert_not_in(self.user2._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_removed")

    def test_edit_node_title(self):
        url = "/api/v1/project/{0}/edit/".format(self.project._id)
        # The title is changed though posting form data
        res = self.app.post_json(url, {"name": "title", "value": "Bacon"},
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
        url = "/api/v1/project/{0}/addtag/{tag}/".format(self.project._primary_key,
                                                        tag="footag")
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_in("footag", self.project.tags)

    def test_remove_tag(self):
        self.project.add_tag("footag", auth=self.consolidate_auth1, save=True)
        assert_in("footag", self.project.tags)
        url = "/api/v1/project/{0}/removetag/{tag}/".format(self.project._primary_key,
                                                        tag="footag")
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_not_in("footag", self.project.tags)

    def test_register_template_page(self):
        url = "/api/v1/project/{0}/register/Replication_Recipe_(Brandt_et_al.,_2013):_Post-Completion/".format(self.project._primary_key)
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        # A registration was added to the project's registration list
        assert_equal(len(self.project.registration_list), 1)
        # A log event was saved
        assert_equal(self.project.logs[-1].action, "project_registered")
        # Most recent node is a registration
        reg = Node.load(self.project.registration_list[-1])
        assert_true(reg.is_registration)

    def test_get_logs(self):
        # Add some logs
        for _ in range(5):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action='file_added',
                    params={'project': self.project._id}
                )
            )
        self.project.save()
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        self.project.reload()
        data = res.json
        assert_equal(len(data['logs']), len(self.project.logs))
        assert_false(data['has_more_logs'])
        most_recent = data['logs'][0]
        assert_equal(most_recent['action'], 'file_added')

    def test_get_logs_with_count_param(self):
        # Add some logs
        for _ in range(5):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action='file_added',
                    params={'project': self.project._id}
                )
            )
        self.project.save()
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url, {'count': 3}, auth=self.auth)
        assert_equal(len(res.json['logs']), 3)
        assert_true(res.json['has_more_logs'])

    def test_get_logs_defaults_to_ten(self):
        # Add some logs
        for _ in range(12):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action='file_added',
                    params={'project': self.project._id}
                )
            )
        self.project.save()
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), 10)
        assert_true(res.json['has_more_logs'])

    def test_get_more_logs(self):
        # Add some logs
        for _ in range(12):
            self.project.logs.append(NodeLogFactory(user=self.user1,
                                                    action="file_added",
                                                    params={"project": self.project._id}))
        self.project.save()
        url = "/api/v1/project/{0}/log/".format(self.project._primary_key)
        res = self.app.get(url, {"pageNum": 1}, auth=self.auth)
        assert_equal(len(res.json['logs']), 4)
        assert_false(res.json['has_more_logs'])

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
                params={'project': self.project._id}
            )
        self.project.is_public = True
        self.project.save()
        child = NodeFactory(project=self.project)
        for _ in range(5):
            child.add_log(
                auth=self.consolidate_auth1,
                action='file_added',
                params={'project': child._id}
            )
        url = '/api/v1/project/{0}/log/'.format(self.project._primary_key)
        res = self.app.get(url).maybe_follow()
        assert_equal(len(res.json['logs']), 10)
        assert_true(res.json['has_more_logs'])
        assert_equal(
            [self.project._id] * 10,
            [
                log['params']['project']
                for log in res.json['logs']
            ]
        )

    def test_logs_from_api_url(self):
        # Add some logs
        for _ in range(12):
            self.project.logs.append(
                NodeLogFactory(
                    user=self.user1,
                    action="file_added",
                    params={"project": self.project._id}
                )
            )
        self.project.save()
        url = "/api/v1/project/{0}/".format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['node']['logs']), 10)
        assert_true(res.json['node']['has_more_logs'])

    def test_remove_project(self):
        url = self.project.api_url
        res = self.app.delete_json(url, {}, auth=self.auth).maybe_follow()
        self.project.reload()
        assert_equal(self.project.is_deleted, True)
        assert_in('url', res.json)
        assert_equal(res.json['url'], '/dashboard/')

    def test_private_link_edit_name(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        assert_equal(link.name, "link")
        url = self.project.api_url + 'private_link/edit/'
        self.app.put_json(url, {'pk': link._id, "value": "new name"}, auth=self.auth).maybe_follow()
        self.project.reload()
        link.reload()
        assert_equal(link.name, "new name")

    def test_remove_private_link(self):
        link = PrivateLinkFactory()
        link.nodes.append(self.project)
        link.save()
        with app.test_request_context():
            url = api_url_for(
                'remove_private_link',
                pid=self.project._primary_key
            )
        self.app.delete_json(url, {'private_link_id': link._id}, auth=self.auth).maybe_follow()
        self.project.reload()
        link.reload()
        assert_true(link.is_deleted)

    def test_remove_component(self):
        node = NodeFactory(project=self.project, creator=self.user1)
        url = node.api_url
        res = self.app.delete_json(url, {}, auth=self.auth).maybe_follow()
        node.reload()
        assert_equal(node.is_deleted, True)
        assert_in('url', res.json)
        assert_equal(res.json['url'], self.project.url)

    def test_cant_remove_component_if_not_admin(self):
        node = NodeFactory(project=self.project, creator=self.user1)
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


class TestUserProfile(OsfTestCase):

    def setUp(self):
        super(TestUserProfile, self).setUp()
        self.app = TestApp(app)
        self.user = AuthUserFactory()

    def test_unserialize_social(self):
        url = api_url_for('unserialize_social')
        payload = {
            'personal': 'http://frozen.pizza.com/reviews',
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

    def test_serialize_social_editable(self):
        self.user.social['twitter'] = 'howtopizza'
        self.user.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert_equal(res.json.get('twitter'), 'howtopizza')
        assert_true(res.json.get('github') is None)
        assert_true(res.json['editable'])

    def test_serialize_social_not_editable(self):
        user2 = AuthUserFactory()
        self.user.social['twitter'] = 'howtopizza'
        self.user.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        )
        assert_equal(res.json.get('twitter'), 'howtopizza')
        assert_true(res.json.get('github') is None)
        assert_false(res.json['editable'])

    def test_serialize_social_addons_editable(self):
        self.user.add_addon('github')
        user_github = self.user.get_addon('github')
        user_github.github_user = 'howtogithub'
        user_github.save()
        url = api_url_for('serialize_social')
        res = self.app.get(
            url,
            auth=self.user.auth,
        )
        assert_equal(
            res.json['addons']['github'],
            'howtogithub'
        )

    def test_serialize_social_addons_not_editable(self):
        user2 = AuthUserFactory()
        self.user.add_addon('github')
        user_github = self.user.get_addon('github')
        user_github.github_user = 'howtogithub'
        user_github.save()
        url = api_url_for('serialize_social', uid=self.user._id)
        res = self.app.get(
            url,
            auth=user2.auth,
        )
        assert_not_in('addons', res.json)


class TestAddingContributorViews(OsfTestCase):

    def setUp(self):
        ensure_schemas()
        self.app = TestApp(app)
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator)
        # Authenticate all requests
        self.app.authenticate(*self.creator.auth)

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

    def test_deserialize_contributors_sends_unreg_contributor_added_signal(self):
        unreg = UnregUserFactory()
        from website.project.model import unreg_contributor_added
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
        with app.test_request_context():
            url = api_url_for(
                'project_contributors_post',
                pid=self.project._primary_key
            )
        self.app.post_json(url, payload).maybe_follow()
        self.project.reload()
        assert_equal(len(self.project.contributors),
            n_contributors_pre + len(payload['users']))

        new_unreg = auth.get_user(username=email)
        assert_false(new_unreg.is_registered)
        # unclaimed record was added
        new_unreg.reload()
        assert_in(self.project._primary_key, new_unreg.unclaimed_records)
        rec = new_unreg.get_unclaimed_record(self.project._primary_key)
        assert_equal(rec['name'], name)
        assert_equal(rec['email'], email)

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_add_contributors_post_only_sends_one_email_to_unreg_user(self,
        mock_send_claim_email):
        # Project has components
        comp1, comp2 = NodeFactory(creator=self.creator), NodeFactory(creator=self.creator)
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
        with app.test_request_context():
            url = api_url_for(
                'project_contributors_post',
                pid=self.project._primary_key
            )
        assert self.project.can_edit(user=self.creator)
        res = self.app.post_json(url, payload, auth=self.creator.auth)

        # finalize_invitation should only have been called once
        assert_equal(mock_send_claim_email.call_count, 1)


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
        with app.test_request_context():
            url = api_url_for('project_contributors_post',
                pid=self.project._primary_key)
        self.app.post_json(url, payload).maybe_follow()
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(email=email))

    def test_add_multiple_contributors_only_adds_one_log(self):
        n_logs_pre = len(self.project.logs)
        reg_user = UserFactory()
        name, email = fake.name(), fake.email()
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
        with app.test_request_context():
            url = api_url_for('project_contributors_post',
                pid=self.project._primary_key)
        res = self.app.post_json(url, payload).maybe_follow()
        self.project.reload()
        assert_equal(len(self.project.logs), n_logs_pre + 1)

    def test_add_contribs_to_multiple_nodes(self):
        child = NodeFactory(project=self.project, creator=self.creator)
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
        res = self.app.post_json(url, payload).maybe_follow()
        child.reload()
        assert_equal(len(child.contributors),
            n_contributors_pre + len(payload['users']))


class TestUserInviteViews(OsfTestCase):

    def setUp(self):
        ensure_schemas()
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = '/api/v1/project/{0}/invite_contributor/'.format(self.project._primary_key)

    def test_invite_contributor_post_if_not_in_db(self):
        name, email = fake.name(), fake.email()
        res = self.app.post_json(self.invite_url,
            {'fullname': name, 'email': email}, auth=self.user.auth)
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
        data =res.json
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
        unreg_user = project.add_unregistered_contributor(fullname=fake.name(),
            email=given_email, auth=Auth(project.creator))
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
            email=given_email, auth=Auth(referrer)
        )
        project.save()
        send_claim_email(email=real_email, user=unreg_user, node=project)

        assert_true(send_mail.called)
        # email was sent to referrer
        assert_true(send_mail.called_with(
            to_addr=referrer.username,
            mail=mails.FORWARD_INVITE
        ))


@unittest.skipIf(not settings.ALLOW_CLAIMING, 'skipping until claiming is fully implemented')
class TestClaimViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
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

        res = self.app.post_json(url,
            payload
        )

        # mail was sent
        assert_true(send_mail.called)
        # ... to the correct address
        assert_true(send_mail.called_with(to_addr=self.given_email))

        # view returns the correct JSON
        assert_equal(res.json, {
            'status': 'success',
            'email': reg_user.username,
            'fullname': self.given_name,
        })

    @mock.patch('website.project.views.contributor.send_claim_registered_email')
    def test_claim_user_post_with_email_already_registered_sends_correct_email(self,
        send_claim_registered_email):
        reg_user = UserFactory()
        payload = {
            'value': reg_user.username,
            'pk': self.user._primary_key
        }
        with app.test_request_context():
            url = api_url_for('claim_user_post', uid=self.user._primary_key,
                pid=self.project._primary_key)
        res = self.app.post_json(url, payload)
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
        with app.test_request_context():
            res = res.follow(auth=reg_user.auth)
            token = self.user.get_unclaimed_record(self.project._primary_key)['token']
            expected = web_url_for('claim_user_registered',
                pid=self.project._primary_key,
                uid=self.user._primary_key,
                token=token)
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
        assert_equal(res.request.path, '/account/')

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
        assert_true(self.user.is_active())
        assert_not_in(self.project._primary_key, self.user.unclaimed_records)

    def test_posting_to_claim_form_removes_all_unclaimed_data(self):
        # user has multiple unclaimed records
        p2 = ProjectFactory(creator=self.referrer)
        self.user.add_unclaimed_record(node=p2, referrer=self.referrer,
            given_name=fake.name())
        self.user.save()
        assert_true(len(self.user.unclaimed_records.keys()) > 1)  # sanity check
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, {
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
        different_name= fake.name()
        new_user = self.project.add_unregistered_contributor(email=unreg.username,
            fullname=different_name,
            auth=Auth(self.referrer))
        self.project.save()
        # Goes to claim url
        claim_url = new_user.get_claim_url(self.project._primary_key)
        res = self.app.post(claim_url, {
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
            {'value': self.given_email, 'pk': self.user._primary_key},
            auth=self.referrer.auth)
        assert_equal(res.json['fullname'], self.given_name)
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(to_addr=self.given_email))

    @mock.patch('website.project.views.contributor.mails.send_mail')
    def test_claim_user_post_if_email_is_different_from_given_email(self, send_mail):
        email = fake.email()  # email that is different from the one the referrer gave
        url = '/api/v1/user/{0}/{1}/claim/email/'.format(self.user._primary_key,
            self.project._primary_key)
        res = self.app.post_json(url,
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
        with app.test_request_context():
            url = web_url_for('claim_user_registered', uid=self.user._primary_key,
                pid=self.project._primary_key, token='badtoken')
        res = self.app.get(url, auth=self.referrer.auth, expect_errors=400)
        assert_equal(res.status_code, 400)

    def test_cannot_claim_user_with_user_who_is_already_contributor(self):
        # user who is already a contirbutor to the project
        contrib = AuthUserFactory.build()
        contrib.set_password('underpressure')
        contrib.save()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        # Claiming user goes to claim url, but contrib is already logged in
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=contrib.auth).follow(auth=contrib.auth, expect_errors=True)
        # Response is a 400
        assert_equal(res.status_code, 400)

class TestWatchViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory.build()
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.consolidate_auth = Auth(user=self.user, api_key=api_key)
        self.auth = ('test', self.user.api_keys[0]._id)  # used for requests auth
        # A public project
        self.project = ProjectFactory(is_public=True)
        self.project.save()
        # Manually reset log date to 100 days ago so it won't show up in feed
        self.project.logs[0].date = dt.datetime.utcnow() - dt.timedelta(days=100)
        self.project.logs[0].save()
        # A log added now
        self.last_log = self.project.add_log(
            NodeLog.TAG_ADDED, params={'project': self.project._primary_key},
            auth=self.consolidate_auth, log_date=dt.datetime.utcnow(),
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
        node = NodeFactory(creator=self.user, project=self.project, is_public=True)
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
            project.logs.append(NodeLogFactory(user=self.user, action="file_added"))
        project.save()
        watch_cfg = WatchConfigFactory(node=project)
        self.user.watch(watch_cfg)
        self.user.save()
        url = "/api/v1/watched/logs/"
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), 10)
        assert_equal(res.json['logs'][0]['action'], 'file_added')

    def test_get_more_watched_logs(self):
        project = ProjectFactory()
        # Add some logs
        for _ in range(12):
            project.logs.append(NodeLogFactory(user=self.user, action="file_added"))
        project.save()
        watch_cfg = WatchConfigFactory(node=project)
        self.user.watch(watch_cfg)
        self.user.save()
        url = "/api/v1/watched/logs/"
        res = self.app.get(url, {"pageNum": 1}, auth=self.auth)
        assert_equal(len(res.json['logs']), 3)
        assert_equal(res.json['logs'][0]['action'], 'file_added')


class TestPointerViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)

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

    def test_add_pointers_not_provided(self):
        url = self.project.api_url + 'pointer/'
        with assert_raises(AppError):
            self.app.post_json(url, {}, auth=self.user.auth)

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
        with assert_raises(AppError):
            self.app.delete_json(url, {}, auth=self.user.auth)

    def test_remove_pointer_not_found(self):
        url = self.project.api_url + 'pointer/'
        with assert_raises(AppError):
            self.app.delete_json(
                url,
                {'pointerId': None},
                auth=self.user.auth
            )

    def test_remove_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/'
        node = NodeFactory()
        pointer = Pointer(node=node)
        with assert_raises(AppError):
            self.app.delete_json(
                url,
                {'pointerId': pointer._id},
                auth=self.user.auth,
            )

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
        with assert_raises(AppError):
            self.app.post_json(url, {}, auth=self.user.auth)

    def test_fork_pointer_not_found(self):
        url = self.project.api_url + 'pointer/fork/'
        with assert_raises(AppError):
            self.app.post_json(
                url,
                {'pointerId': None},
                auth=self.user.auth
            )

    def test_fork_pointer_not_in_nodes(self):
        url = self.project.api_url + 'pointer/fork/'
        node = NodeFactory()
        pointer = Pointer(node=node)
        with assert_raises(AppError):
            self.app.post_json(
                url,
                {'pointerId': pointer._id},
                auth=self.user.auth
            )

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
        "Assert that link warning appears in before fork callback."
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
        "Assert that link warning does not appear in before register callback."
        url = self.project.api_url + 'fork/before/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your fork' in prompt
        ]
        assert_equal(len(prompts), 0)

    def test_before_fork_no_pointer(self):
        "Assert that link warning does not appear in before fork callback."
        url = self.project.api_url + 'beforeregister/'
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        prompts = [
            prompt
            for prompt in res.json['prompts']
            if 'Links will be copied into your registration' in prompt
        ]
        assert_equal(len(prompts), 0)


class TestPublicViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)

    def test_explore(self):
        res = self.app.get("/explore/").maybe_follow()
        assert_equal(res.status_code, 200)


class TestAuthViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.auth = self.user.auth

    def test_merge_user(self):
        dupe = UserFactory(username="copy@cat.com",
                            emails=['copy@cat.com'])
        dupe.set_password("copycat")
        dupe.save()
        url = "/api/v1/user/merge/"
        res = self.app.post_json(url, {"merged_username": "copy@cat.com",
                                        "merged_password": "copycat"}, auth=self.auth)
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

    def test_register_ok(self):
        with app.test_request_context():
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

    def test_register_email_mismatch(self):
        with app.test_request_context():
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
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        users = User.find(Q('username', 'eq', email))
        assert_equal(users.count(), 0)

    def test_register_sends_user_registered_signal(self):
        with app.test_request_context():
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
        assert_equal(mock_signals.signals_sent(), set([auth.signals.user_registered]))

    def test_register_post_sends_user_registered_signal(self):
        with app.test_request_context():
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
        assert_equal(mock_signals.signals_sent(), set([auth.signals.user_registered]))

    def test_resend_confirmation_get(self):
        res = self.app.get('/resend/')
        assert_equal(res.status_code, 200)

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_post_sends_confirm_email(self, send_mail):
        # Make sure user has a confirmation token for their primary email
        self.user.add_email_verification(self.user.username)
        self.user.save()
        res = self.app.post('/resend/', {'email': self.user.username})
        assert_true(send_mail.called)
        assert_true(send_mail.called_with(
            to_addr=self.user.username
        ))

    @mock.patch('framework.auth.views.mails.send_mail')
    def test_resend_confirmation_post_if_user_not_in_database(self, send_mail):
        res = self.app.post('/resend/', {'email': 'norecord@norecord.no'})
        assert_false(send_mail.called)

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

    def test_expired_link_returns_400(self):
        user = User.create_unconfirmed('brian1@queen.com', 'bicycle123', 'Brian May')
        user.save()
        token = user.get_confirmation_token('brian1@queen.com')
        url = user.get_confirmation_url('brian1@queen.com', external=False)
        user.confirm_email(token)
        user.save()
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, http.BAD_REQUEST)


# TODO: Use mock add-on
class TestAddonUserViews(OsfTestCase):

    def setUp(self):
        self.user = AuthUserFactory()
        self.app = TestApp(app)

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
        """Add, then delete, add-ons; assert that add-ons are not attached to
        project.

        """
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


# TODO: Move to OSF Storage
class TestFileViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.project = ProjectFactory.build(creator=self.user, is_public=True)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_files_get(self):
        url = '/api/v1/{0}/files/'.format(self.project._primary_key)
        with app.test_request_context():
            res = self.app.get(url, auth=self.user.auth).maybe_follow()
            expected = _view_project(self.project, auth=Auth(user=self.user))
        assert_equal(res.status_code, http.OK)
        assert_equal(res.json['node'], expected['node'])
        assert_in('tree_js', res.json)
        assert_in('tree_css', res.json)

    def test_grid_data(self):
        url = '/api/v1/{0}/files/grid/'.format(self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, http.OK)
        expected = rubeus.to_hgrid(self.project, auth=Auth(self.user))
        data = res.json['data']
        assert_equal(len(data), len(expected))


class TestComments(OsfTestCase):

    def setUp(self):
        self.project = ProjectFactory(is_public=True)
        self.consolidated_auth = Auth(user=self.project.creator)
        self.non_contributor = AuthUserFactory()
        self.app = TestApp(app)

    def _configure_project(self, project, comment_level):

        project.comment_level = comment_level
        project.save()

    def _add_comment(self, project, content=None, **kwargs):

        content = content if content is not None else 'hammer to fall'
        url = project.api_url + 'comment/'
        return self.app.post_json(
            url,
            {
                'content': content,
                'isPublic': 'public',
            },
            **kwargs
        )

    def test_add_comment_public_contributor(self):

        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        self.project.reload()

        assert_equal(len(self.project.commented), 1)
        assert_equal(
            res.json['comment'],
            serialize_comment(
                self.project.commented[0], self.consolidated_auth
            )
        )

    def test_add_comment_public_non_contributor(self):

        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, auth=self.non_contributor.auth,
        )

        self.project.reload()

        assert_equal(len(self.project.commented), 1)
        assert_equal(
            res.json['comment'],
            serialize_comment(
                self.project.commented[0], Auth(user=self.non_contributor)
            )
        )

    def test_add_comment_private_contributor(self):

        self._configure_project(self.project, 'private')
        res = self._add_comment(
            self.project, auth=self.project.creator.auth,
        )

        self.project.reload()

        assert_equal(len(self.project.commented), 1)
        assert_equal(
            res.json['comment'],
            serialize_comment(
                self.project.commented[0], self.consolidated_auth
            )
        )

    def test_add_comment_private_non_contributor(self):

        self._configure_project(self.project, 'private')
        res = self._add_comment(
            self.project, auth=self.non_contributor.auth, expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

    def test_add_comment_logged_out(self):

        self._configure_project(self.project, 'public')
        res = self._add_comment(self.project)

        assert_equal(res.status_code, 302)
        assert_in('next=', res.headers.get('location'))

    def test_add_comment_off(self):

        self._configure_project(self.project, None)
        res = self._add_comment(
            self.project, auth=self.project.creator.auth, expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_add_comment_empty(self):
        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, content='',
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_false(getattr(self.project, 'commented', []))

    def test_add_comment_toolong(self):
        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, content='toolong' * 500,
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_false(getattr(self.project, 'commented', []))

    def test_add_comment_whitespace(self):
        self._configure_project(self.project, 'public')
        res = self._add_comment(
            self.project, content='  ',
            auth=self.project.creator.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_false(getattr(self.project, 'commented', []))

    def test_edit_comment(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project)

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'edited',
                'isPublic': 'private',
            },
            auth=self.project.creator.auth,
        )

        comment.reload()

        assert_equal(res.json['content'], 'edited')

        assert_equal(comment.content, 'edited')

    def test_edit_comment_short(self):
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, content='short')
        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': '',
                'isPublic': 'private',
            },
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        comment.reload()
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(comment.content, 'short')


    def test_edit_comment_toolong(self):
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, content='short')
        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'toolong' * 500,
                'isPublic': 'private',
            },
            auth=self.project.creator.auth,
            expect_errors=True,
        )
        comment.reload()
        assert_equal(res.status_code, http.BAD_REQUEST)
        assert_equal(comment.content, 'short')

    def test_edit_comment_non_author(self):
        "Contributors who are not the comment author cannot edit."
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project)
        non_author = AuthUserFactory()
        self.project.add_contributor(non_author, auth=self.consolidated_auth)

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'edited',
                'isPublic': 'private',
            },
            auth=non_author.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

    def test_edit_comment_non_contributor(self):
        "Non-contributors who are not the comment author cannot edit."
        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project)

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.put_json(
            url,
            {
                'content': 'edited',
                'isPublic': 'private',
            },
            auth=self.non_contributor.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

    def test_delete_comment_author(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project)

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        self.app.delete_json(
            url,
            auth=self.project.creator.auth,
        )

        comment.reload()

        assert_true(comment.is_deleted)

    def test_delete_comment_non_author(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project)

        url = self.project.api_url + 'comment/{0}/'.format(comment._id)
        res = self.app.delete_json(
            url,
            auth=self.non_contributor.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.FORBIDDEN)

        comment.reload()

        assert_false(comment.is_deleted)

    def test_report_abuse(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project)
        reporter = AuthUserFactory()

        url = self.project.api_url + 'comment/{0}/report/'.format(comment._id)

        self.app.post_json(
            url,
            {
                'category': 'spam',
                'text': 'ads',
            },
            auth=reporter.auth,
        )

        comment.reload()
        assert_in(reporter._id, comment.reports)
        assert_equal(
            comment.reports[reporter._id],
            {'category': 'spam', 'text': 'ads'}
        )

    def test_can_view_private_comments_if_contributor(self):

        self._configure_project(self.project, 'public')
        comment = CommentFactory(node=self.project, user=self.project.creator, is_public=False)

        url = self.project.api_url + 'comments/'
        res = self.app.get(url, auth=self.project.creator.auth)

        assert_equal(len(res.json['comments']), 1)

    def test_discussion_recursive(self):

        self._configure_project(self.project, 'public')
        comment_l0 = CommentFactory(node=self.project)

        user_l1 = UserFactory()
        user_l2 = UserFactory()
        comment_l1 = CommentFactory(node=self.project, target=comment_l0, user=user_l1)
        comment_l2 = CommentFactory(node=self.project, target=comment_l1, user=user_l2)

        url = self.project.api_url + 'comments/discussion/'
        res = self.app.get(url)

        assert_equal(len(res.json['discussion']), 3)

    def test_discussion_no_repeats(self):

        self._configure_project(self.project, 'public')
        comment_l0 = CommentFactory(node=self.project)

        comment_l1 = CommentFactory(node=self.project, target=comment_l0)
        comment_l2 = CommentFactory(node=self.project, target=comment_l1)

        url = self.project.api_url + 'comments/discussion/'
        res = self.app.get(url)

        assert_equal(len(res.json['discussion']), 1)

    def test_discussion_sort(self):

        self._configure_project(self.project, 'public')

        user1 = UserFactory()
        user2 = UserFactory()

        CommentFactory(node=self.project)
        for _ in range(3):
            CommentFactory(node=self.project, user=user1)
        for _ in range(2):
            CommentFactory(node=self.project, user=user2)

        url = self.project.api_url + 'comments/discussion/'
        res = self.app.get(url)

        assert_equal(len(res.json['discussion']), 3)
        observed = [user['id'] for user in res.json['discussion']]
        expected = [user1._id, user2._id, self.project.creator._id]
        assert_equal(observed, expected)


class TestTagViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_tag_get_returns_200(self):
        with app.test_request_context():
            url = web_url_for('project_tag', tag='foo')
        res = self.app.get(url)
        assert_equal(res.status_code, 200)


@requires_search
class TestSearchViews(OsfTestCase):

    def setUp(self):
        import website.search.search as search
        search.delete_all()
        self.app = TestApp(app)
        self.project = ProjectFactory(creator=UserFactory(fullname='Robbie Williams'))
        self.contrib1 = UserFactory(fullname='Freddie Mercury')
        self.contrib2 = UserFactory(fullname='Brian May')

    def test_search_contributor(self):
        with app.test_request_context():
            url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': self.contrib1.fullname})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        assert_equal(len(result), 1)
        freddie = result[0]
        assert_equal(freddie['fullname'], self.contrib1.fullname)
        assert_in('gravatar_url', freddie)
        assert_equal(freddie['registered'], self.contrib1.is_registered)
        assert_equal(freddie['active'], self.contrib1.is_active())

    def test_search_projects(self):
        with app.test_request_context():
            url = web_url_for('search_search')
        res = self.app.get(url, {'q': self.project.title})
        assert_equal(res.status_code, 200)
    def tearDown(self):
        import website.search.search as search
        search.delete_all()

class TestReorderComponents(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.creator = AuthUserFactory()
        self.contrib = AuthUserFactory()
        # Project is public
        self.project = ProjectFactory.build(creator=self.creator, public=True)
        self.project.add_contributor(self.contrib, auth=Auth(self.creator))

        # subcomponent that only creator can see
        self.public_component = NodeFactory(creator=self.creator, public=True)
        self.private_component = NodeFactory(creator=self.creator, public=False)
        self.project.nodes.append(self.public_component)
        self.project.nodes.append(self.private_component)

        self.project.save()

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_reorder_components_with_private_component(self):

        # contrib tries to reorder components
        payload = {'new_list': [
                '{0}:node'.format(self.private_component._primary_key),
                '{0}:node'.format(self.public_component._primary_key),
            ]
        }
        url = lookup('api', 'project_reorder_components', pid=self.project._primary_key)
        res = self.app.post_json(url, payload, auth=self.contrib.auth)
        assert_equal(res.status_code, 200)


class TestDashboardViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)

        self.creator = AuthUserFactory()
        self.contrib = AuthUserFactory()

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/571
    def test_components_with__are_accessible_from_dashboard(self):
        project = ProjectFactory(creator=self.creator, public=False)
        component = NodeFactory(creator=self.creator, project=project)
        component.add_contributor(self.contrib, auth=Auth(self.creator))
        component.save()

        url = lookup('api', 'get_dashboard_nodes')
        res = self.app.get(url, auth=self.contrib.auth)

        assert_equal(len(res.json['nodes']), 1)


if __name__ == '__main__':
    unittest.main()
