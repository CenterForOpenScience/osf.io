#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Views tests for Node/Project watching.'''
from __future__ import absolute_import
import os
import unittest
import datetime as dt
from nose.tools import *  # PEP8 asserts
import requests

from website.project.model import WatchConfig
from tests.base import OsfTestCase
from tests.factories import (UserFactory, ApiKeyFactory, ProjectFactory,
                            WatchConfigFactory, NodeFactory)

PORT = int(os.environ.get("OSF_PORT", '5000'))
BASE_URL = "http://localhost:{port}".format(port=PORT)


class TestWatchViews(OsfTestCase):

    def setUp(self):
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
        url = BASE_URL + '/api/v1/project/{0}/watch/'.format(self.project._id)
        res = requests.post(url,
                            data={},
                            auth=self.auth)
        self.user.reload()
        n_watched_now = len(self.user.watched)
        assert_equal(res.status_code, 200)
        assert_equal(n_watched_now, n_watched_then + 1)

    def test_watching_project_twice_returns_400(self):
        url = BASE_URL + "/api/v1/project/{0}/watch/".format(self.project._id)
        res = requests.post(url,
                            data={},
                            auth=self.auth)
        assert_equal(res.status_code, 200)
        # User tries to watch a node she's already watching
        res2 = requests.post(url,
                            data={},
                            auth=self.auth)
        assert_equal(res2.status_code, 400)

    def test_unwatching_a_project_removes_from_watched_list(self):
        # The user has already watched a project
        watch_config = WatchConfigFactory(node=self.project)
        self.user.watch(watch_config)
        self.user.save()
        n_watched_then = len(self.user.watched)
        url = BASE_URL + '/api/v1/project/{0}/unwatch/'.format(self.project._id)
        res = requests.post(url,
                            data={},
                            auth=self.auth)
        self.user.reload()
        n_watched_now = len(self.user.watched)
        assert_equal(res.status_code, 200)
        assert_equal(n_watched_now, n_watched_then - 1)
        assert_false(self.user.is_watching(self.project))

    def test_toggle_watch(self):
        # The user is not watching project
        assert_false(self.user.is_watching(self.project))
        url = BASE_URL + "/api/v1/project/{0}/togglewatch/".format(self.project._id)
        res = requests.post(url, data={}, auth=self.auth)
        assert_equal(res.status_code, 200)
        self.user.reload()
        # The user is now watching the project
        assert_true(res.json()['watched'])
        assert_true(self.user.is_watching(self.project))

    def test_toggle_watch_node(self):
        # The project has a public sub-node
        node = NodeFactory(is_public=True)
        self.project.nodes.append(node)
        self.project.save()
        url = BASE_URL + "/api/v1/project/{}/node/{}/togglewatch/".format(self.project._id,
                                                                            node._id)
        res = requests.post(url, data={}, auth=self.auth)
        assert_equal(res.status_code, 200)
        self.user.reload()
        # The user is now watching the sub-node
        assert_true(res.json()['watched'])
        assert_true(self.user.is_watching(node))

if __name__ == '__main__':
    unittest.main()
