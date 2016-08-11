# -*- coding: utf-8 -*-
"""
Unit tests for analytics logic in framework/analytics/__init__.py
"""

import unittest

from nose.tools import *  # flake8: noqa  (PEP8 asserts)
from flask import Flask

from datetime import datetime

from framework import analytics, sessions
from framework.sessions import session

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory


class TestAnalytics(OsfTestCase):

    def test_get_total_activity_count(self):
        user = UserFactory()
        date = datetime.utcnow()

        assert_equal(analytics.get_total_activity_count(user._id), 0)
        assert_equal(analytics.get_total_activity_count(user._id), user.get_activity_points(db=self.db))

        analytics.increment_user_activity_counters(user._id, 'project_created', date.isoformat(), db=self.db)

        assert_equal(analytics.get_total_activity_count(user._id, db=self.db), 1)
        assert_equal(analytics.get_total_activity_count(user._id, db=self.db), user.get_activity_points(db=self.db))

    def test_increment_user_activity_counters(self):
        user = UserFactory()
        date = datetime.utcnow()

        assert_equal(user.get_activity_points(db=self.db), 0)
        analytics.increment_user_activity_counters(user._id, 'project_created', date.isoformat(), db=self.db)
        assert_equal(user.get_activity_points(db=self.db), 1)


class UpdateCountersTestCase(OsfTestCase):

    def setUp(self):
        decoratorapp = Flask('decorators')
        self.ctx = decoratorapp.test_request_context()
        self.ctx.push()
        # TODO: Think of something better @sloria @jmcarp
        sessions.set_session(sessions.Session())

    def tearDown(self):
        self.ctx.pop()


class TestUpdateCounters(UpdateCountersTestCase):

    def setUp(self):
        super(TestUpdateCounters, self).setUp()
        self.node = ProjectFactory()
        self.fid = 'foo'
        self.vid = 1

    def test_update_counters_file(self):

        @analytics.update_counters('download:{target_id}:{fid}', db=self.db)
        def download_file_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node, self.fid), db=self.db)
        assert_equal(count, (None, None))

        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node, self.fid), db=self.db)
        assert_equal(count, (1, 1))

        page = 'download:{0}:{1}'.format(self.node, self.fid)

        session.data['visited'].append(page)
        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node, self.fid), db=self.db)
        assert_equal(count, (1, 2))

    def test_update_counters_file_version(self):
        @analytics.update_counters('download:{target_id}:{fid}:{vid}', db=self.db)
        def download_file_version_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        count = analytics.get_basic_counters('download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid), db=self.db)
        assert_equal(count, (None, None))

        download_file_version_(node=self.node, fid=self.fid, vid=self.vid)

        count = analytics.get_basic_counters('download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid), db=self.db)
        assert_equal(count, (1, 1))

        page = 'download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid)

        session.data['visited'].append(page)
        download_file_version_(node=self.node, fid=self.fid, vid=self.vid)

        count = analytics.get_basic_counters('download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid), db=self.db)
        assert_equal(count, (1, 2))

    def test_get_basic_counters(self):
        page = 'node:' + str(self.node._id)

        d = {'$inc': {}}
        d['$inc']['total'] = 5
        d['$inc']['unique'] = 3

        collection = self.db['pagecounters']
        collection.update({'_id': page}, d, True, False)
        count = analytics.get_basic_counters(page, db=self.db)
        assert_equal(count, (3, 5))

    @unittest.skip('Reverted the fix for #2281. Unskip this once we use GUIDs for keys in the download counts collection')
    def test_update_counters_different_files(self):
        # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2281
        @analytics.update_counters('download:{target_id}:{fid}', db=self.db)
        def download_file_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        fid1 = 'test.analytics.py'
        fid2 = 'test_analytics.py'

        download_file_(node=self.node, fid=fid1)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node, fid1), db=self.db)
        assert_equal(count, (1, 1))
        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node, fid2), db=self.db)
        assert_equal(count, (None, None))

        page = 'download:{0}:{1}'.format(self.node, fid1)

        session.data['visited'].append(page)
        download_file_(node=self.node, fid=fid1)
        download_file_(node=self.node, fid=fid2)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node, fid1), db=self.db)
        assert_equal(count, (1, 2))
        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node, fid2), db=self.db)
        assert_equal(count, (1, 1))
