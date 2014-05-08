#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Unit tests for Node/Project watching.'''
from __future__ import absolute_import
import unittest
import datetime as dt

from pytz import utc
from nose.tools import *  # PEP8 asserts
import bson
from framework.auth.decorators import Auth
from tests.base import OsfTestCase
from tests.factories import (UserFactory, ProjectFactory, ApiKeyFactory,
                            WatchConfigFactory)


class TestWatching(OsfTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        # add some log objects
        api_key = ApiKeyFactory()
        self.user.api_keys.append(api_key)
        self.user.save()
        self.consolidate_auth = Auth(user=self.user, api_key=api_key)
        # Clear project logs
        self.project.logs = []
        self.project.save()
        # A log added 100 days ago
        self.project.add_log('project_created',
                        params={'project': self.project._primary_key},
                        auth=self.consolidate_auth,
                        log_date=dt.datetime.utcnow() - dt.timedelta(days=100),
                        save=True)
        # Set the ObjectId to correspond with the log date
        # A log added now
        self.last_log = self.project.add_log('tag_added', params={'project': self.project._primary_key},
                        auth=self.consolidate_auth, log_date=dt.datetime.utcnow(),
                        save=True)
        # Clear watched list
        self.user.watched = []
        self.user.save()

    def test_watch_adds_to_watched_list(self):
        n_watched_then = len(self.user.watched)
        # A user watches a WatchConfig
        config = WatchConfigFactory(node=self.project)
        self.user.watch(config, save=True)
        n_watched_now = len(self.user.watched)
        assert_equal(n_watched_now, n_watched_then + 1)
        assert_true(self.user.is_watching(self.project))

    def test_unwatch_removes_from_watched_list(self):
        # The user has already watched a project
        self._watch_project(self.project)
        config = WatchConfigFactory(node=self.project)
        n_watched_then = len(self.user.watched)
        self.user.unwatch(config)
        n_watched_now = len(self.user.watched)
        assert_equal(n_watched_now, n_watched_then - 1)
        assert_false(self.user.is_watching(self.project))

    @unittest.skip("Won't work because the old log's id doesn't encode the correct log date")
    def test_get_recent_log_ids(self):
        self._watch_project(self.project)
        log_ids = list(self.user.get_recent_log_ids())
        assert_equal(self.last_log._id, log_ids[0])
        # This part won't work
        # TODO(sloria): Rethink.
        assert_equal(len(log_ids), 1)

    def test_get_recent_log_ids_since(self):
        self._watch_project(self.project)
        since = dt.datetime.utcnow().replace(tzinfo=utc) - dt.timedelta(days=101)
        log_ids = list(self.user.get_recent_log_ids(since=since))
        assert_equal(len(log_ids), 2)

    def test_get_daily_digest_log_ids(self):
        self._watch_project(self.project)
        day_log_ids = list(self.user.get_daily_digest_log_ids())
        assert_in(self.last_log._id, day_log_ids)

    def _watch_project(self, project):
        watch_config = WatchConfigFactory(node=project)
        self.user.watch(watch_config)
        self.user.save()

    def _unwatch_project(self, project):
        watch_config = WatchConfigFactory(node=project)
        self.user.watch(watch_config)
        self.user.save()

if __name__ == '__main__':
    unittest.main()
