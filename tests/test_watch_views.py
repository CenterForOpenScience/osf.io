#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Views tests for Node/Project watching.'''
from __future__ import absolute_import
import unittest
import datetime as dt
from nose.tools import *  # PEP8 asserts
from website.models import User, Node, WatchConfig
from framework import Q
import requests

BASE_URL = "http://localhost:5000"  # FIXME(sloria): Hardcoded port


class TestWatchViews(unittest.TestCase):

    def setUp(self):
        # FIXME(sloria): This affects the development database;
        # Assumes a user and project have been created. Use
        # fixtures/factories in a test db later
        self.user = User.load("Or8W0")
        print(self.user)
        self.auth = (self.user.api_keys[0]._id, 'test')
        # The first project
        self.project = Node.find(Q('category', 'eq', 'project'))[0]
        # add some log objects
        # A log added 100 days ago
        self.project.add_log('project_created',
                        params={'project': self.project._primary_key},
                        user=self.user, log_date=dt.datetime.utcnow() - dt.timedelta(days=100),
                        api_key=self.auth[0],
                        do_save=True)
        # A log added now
        self.last_log = self.project.add_log('tag_added', params={'project': self.project._primary_key},
                        user=self.user, log_date=dt.datetime.utcnow(),
                        api_key=self.auth[0],
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
        watch_config = WatchConfig(node=self.project)
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


if __name__ == '__main__':
    unittest.main()
