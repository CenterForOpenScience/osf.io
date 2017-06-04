#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Unit tests for Node/Project watching.'''
from __future__ import absolute_import
import unittest
import datetime as dt

from pytz import utc
from nose.tools import *  # flake8: noqa (PEP8 asserts)
from framework.auth import Auth
from framework.exceptions import HTTPError
from tests.base import OsfTestCase
from tests.factories import (UserFactory, ProjectFactory,
                             WatchConfigFactory)
from website.views import paginate
import math

class TestWatching(OsfTestCase):

    def setUp(self):
        super(TestWatching, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)
        # add some log objects
        self.consolidate_auth = Auth(user=self.user)
        self.project.save()
        # A log added 100 days ago
        self.project.add_log(
            'tag_added',
            params={'project': self.project._primary_key},
            auth=self.consolidate_auth,
            log_date=dt.datetime.utcnow() - dt.timedelta(days=100),
            save=True,
        )
        # Set the ObjectId to correspond with the log date
        # A log added now
        self.last_log = self.project.add_log(
            'tag_added',
            params={'project': self.project._primary_key},
            auth=self.consolidate_auth, log_date=dt.datetime.utcnow(),
            save=True,
        )
        # Clear watched list
        self.user.watched = []
        self.user.save()

    def test_watch_adds_to_watched_list(self):
        n_watched_then = len(self.user.watched)
        # A user watches a WatchConfig
        config = WatchConfigFactory(node=self.project)
        self.user.watch(config)
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

    @unittest.skip("Won't work because the old log's id doesn't encode the "
                   "correct log date")
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
        assert_equal(len(log_ids), 3)

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

    def test_paginate_helper(self):
        self._watch_project(self.project)
        logs = list(self.user.get_recent_log_ids())
        size = 10
        page = 0
        total = len(logs)
        paginated_logs, pages = paginate(
            self.user.get_recent_log_ids(), total, page, size)
        page_num = math.ceil(total / float(size))
        assert_equal(len(list(paginated_logs)), total)
        assert_equal(page_num, pages)

    def test_paginate_no_negative_page_num(self):
        self._watch_project(self.project)
        logs = list(self.user.get_recent_log_ids())
        size = 10
        page = -1
        total = len(logs)
        with assert_raises(HTTPError):
            paginate(self.user.get_recent_log_ids(), total, page, size)

    def test_paginate_not_go_beyond_limit(self):
        self._watch_project(self.project)
        logs = list(self.user.get_recent_log_ids())
        size = 10
        total = len(logs)
        pages_num = math.ceil(total / float(size))
        page = pages_num
        with assert_raises(HTTPError):
            paginate(self.user.get_recent_log_ids(), total, page, size)

if __name__ == '__main__':
    unittest.main()
