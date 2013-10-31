#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Views tests for the OSF.'''
from __future__ import absolute_import
import json
import unittest
import datetime as dt

from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp

import website.app
from website.models import Node

from tests.base import DbTestCase
from tests.factories import (UserFactory, ApiKeyFactory, ProjectFactory,
                            WatchConfigFactory, NodeFactory, NodeLogFactory)


app = website.app.init_app(routes=True, set_backends=False,
                            settings_module="website.settings")


class TestProjectViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user1 = UserFactory.build()
        # Add an API key for quicker authentication
        api_key = ApiKeyFactory()
        self.user1.api_keys.append(api_key)
        self.user1.save()
        self.auth = ('test', api_key._primary_key)
        self.user2 = UserFactory()
        # A project has 2 contributors
        self.project = ProjectFactory(title="Ham", creator=self.user1)
        self.project.add_contributor(self.user1)
        self.project.add_contributor(self.user2)
        self.project.api_keys.append(api_key)
        self.project.save()

    def test_project_api_url(self):
        url = self.project.api_url
        res = self.app.get(url, auth=self.auth)
        data = res.json
        assert_equal(data['node_category'], 'project')
        assert_equal(data['node_title'], self.project.title)
        assert_equal(data['node_is_public'], self.project.is_public)
        assert_equal(data['node_is_registration'], False)
        assert_equal(data['node_id'], self.project._primary_key)
        assert_equal(data['node_watched_count'], 0)
        assert_true(data['user_is_contributor'])
        assert_equal(data['logs'][-1]['action'], 'project_created')

    def test_add_contributor_post(self):
        # A user is added as a contributor via a POST request
        user = UserFactory()
        url = "/api/v1/project/{0}/addcontributors/".format(self.project._id)
        res = self.app.post(url, json.dumps({"user_ids": [user._id]}),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        self.project.reload()
        assert_in(user._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_added")

    @unittest.skip('Adding non-registered contributors is on hold until '
                   'invitations and account merging are done.')
    def test_add_non_registered_contributor(self):
        url = "/api/v1/project/{0}/addcontributor/".format(self.project._id)
        # A non-registered user is added
        res = self.app.post(url, json.dumps({"email": "joe@example.com", "fullname": "Joe Dirt"}),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        self.project.reload()
        # The contributor list should have length 3 (2 registered, 1 unregistered)
        assert_equal(len(self.project.contributor_list), 3)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_added")

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

    @unittest.skip('Removing non-registered contributors is on hold until '
                   'invitations and account merging are done.')
    def test_project_remove_non_registered_contributor(self):
        # A non-registered user is added to the project
        self.project.add_nonregistered_contributor(name="Vanilla Ice",
                                                    email="iceice@baby.ice",
                                                    user=self.user1)
        self.project.save()
        url = "/api/v1/project/{0}/removecontributors/".format(self.project._id)
        # the contributor is removed via the API
        assert False, 'finish me'


    def test_edit_node_title(self):
        url = "/api/v1/project/{0}/edit/".format(self.project._id)
        # The title is changed though posting form data
        res = self.app.post(url, {"name": "title", "value": "Bacon"},
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

    def test_add_tag(self):
        url = "/api/v1/project/{0}/addtag/{tag}/".format(self.project._primary_key,
                                                        tag="footag")
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_in("footag", self.project.tags)

    def test_remove_tag(self):
        self.project.add_tag("footag", user=self.user1, api_key=None, save=True)
        assert_in("footag", self.project.tags)
        url = "/api/v1/project/{0}/removetag/{tag}/".format(self.project._primary_key,
                                                        tag="footag")
        res = self.app.post_json(url, {}, auth=self.auth)
        self.project.reload()
        assert_not_in("footag", self.project.tags)

    def test_register_template_page(self):
        url = "/api/v1/project/{0}/register/FooBar_Template/".format(self.project._primary_key)
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
            self.project.logs.append(NodeLogFactory(user=self.user1, action="file_added"))
        self.project.save()
        url = "/api/v1/project/{0}/log/".format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        self.project.reload()
        data = res.json
        assert_equal(len(data['logs']), len(self.project.logs))
        most_recent = data['logs'][0]
        assert_equal(most_recent['action'], "file_added")

    def test_get_logs_with_count_param(self):
        # Add some logs
        for _ in range(5):
            self.project.logs.append(NodeLogFactory(user=self.user1, action="file_added"))
        self.project.save()
        url = "/api/v1/project/{0}/log/".format(self.project._primary_key)
        res = self.app.get(url, {"count": 3}, auth=self.auth)
        assert_equal(len(res.json['logs']), 3)

    def test_get_logs_defaults_to_ten(self):
        # Add some logs
        for _ in range(12):
            self.project.logs.append(NodeLogFactory(user=self.user1, action="file_added"))
        self.project.save()
        url = "/api/v1/project/{0}/log/".format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), 10)

    def test_logs_from_api_url(self):
        # Add some logs
        for _ in range(12):
            self.project.logs.append(NodeLogFactory(user=self.user1, action="file_added"))
        self.project.save()
        url = "/api/v1/project/{0}/".format(self.project._primary_key)
        res = self.app.get(url, auth=self.auth)
        assert_equal(len(res.json['logs']), 10)


class TestWatchViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = UserFactory.build(username='tesla@electric.com')
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.auth = ('test', self.user.api_keys[0]._id)  # used for requests auth
        # A public project
        self.project = ProjectFactory(is_public=True)
        self.project.save()
        # add some log objects
        # A log added 100 days ago
        self.project.add_log('project_created',
                        params={'project': self.project._primary_key},
                        user=self.user, log_date=dt.datetime.utcnow() - dt.timedelta(days=100),
                        api_key=self.auth[1],
                        do_save=True)
        # A log added now
        self.last_log = self.project.add_log('tag_added', params={'project': self.project._primary_key},
                        user=self.user, log_date=dt.datetime.utcnow(),
                        api_key=self.auth[1],
                        do_save=True)
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
        assert_equal(res2.status_code, 400)

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
        node = NodeFactory(is_public=True)
        self.project.nodes.append(node)
        self.project.save()
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
        assert_equal(len(res.json['logs']), len(project.logs))
        assert_equal(res.json['logs'][0]['action'], 'file_added')

class TestPublicViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)

    def test_explore(self):
        res = self.app.get("/explore/").maybe_follow()
        assert_equal(res.status_code, 200)

if __name__ == '__main__':
    unittest.main()
