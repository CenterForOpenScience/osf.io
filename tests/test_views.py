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

from tests.base import DbTestCase
from tests.factories import (UserFactory, ApiKeyFactory, ProjectFactory,
                            WatchConfigFactory, NodeFactory)

app = website.app.init_app(routes=True, set_backends=False, settings_module="website.settings")


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

    def test_add_contributor_post(self):
        # A user is added as a contributor via a POST request
        user = UserFactory()
        url = "/api/v1/project/{0}/addcontributor/".format(self.project._id)
        res = self.app.post(url, json.dumps({"user_id": user._id}),
                            content_type="application/json",
                            auth=self.auth).maybe_follow()
        self.project.reload()
        assert_in(user._id, self.project.contributors)
        # A log event was added
        assert_equal(self.project.logs[-1].action, "contributor_added")

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

if __name__ == '__main__':
    unittest.main()
