# -*- coding: utf-8 -*-
"""
Unit tests for analytics logic in framework/analytics/__init__.py
"""

from nose.tools import *

from flask import Flask

from framework import sessions
from framework.analytics import *

from datetime import datetime

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory


class TestAnalytics(OsfTestCase):

    def test_get_total_activity_count(self):
        user = UserFactory()
        date = datetime.utcnow()

        assert_equal(get_total_activity_count(user._id), 0)
        assert_equal(get_total_activity_count(user._id), user.activity_points)

        increment_user_activity_counters(user._id, 'project_created', date)

        assert_equal(get_total_activity_count(user._id), 1)
        assert_equal(get_total_activity_count(user._id), user.activity_points)

    def test_increment_user_activity_counters(self):
        user = UserFactory()
        date = datetime.utcnow()

        assert_equal(user.activity_points, 0)
        increment_user_activity_counters(user._id, 'project_created', date)
        assert_equal(user.activity_points, 1)


# Flask app for testing update_counters decorator
decoratorapp = Flask('decorators')

# Dummy functions for testing update_counters decorator
@update_counters('download:{target_id}:{fid}')
def download_file_(**kwargs):
    return kwargs.get('node') or kwargs.get('project')

@update_counters('download:{target_id}:{fid}:{vid}')
def download_file_version_(**kwargs):
    return kwargs.get('node') or kwargs.get('project')


class UpdateCountersTestCase(OsfTestCase):

    def setUp(self):
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
        count = get_basic_counters('download:{0}:{1}'.format(self.node, self.fid))
        assert_equal(count, (None,None))

        download_file_(node=self.node, fid=self.fid)

        count = get_basic_counters('download:{0}:{1}'.format(self.node, self.fid))
        assert_equal(count, (1,1))

    def test_update_counters_file_version(self):
        count = get_basic_counters('download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid))
        assert_equal(count, (None,None))

        download_file_version_(node=self.node, fid=self.fid, vid=self.vid)

        count = get_basic_counters('download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid))
        assert_equal(count, (1,1))

    def test_update_counters_file_unique(self):
        count = get_basic_counters('download:{0}:{1}'.format(self.node, self.fid))
        assert_equal(count, (None,None))

        page = 'download:{0}:{1}'.format(self.node, self.fid)

        download_file_(node=self.node, fid=self.fid)
        session.data['visited'].append(page)
        download_file_(node=self.node, fid=self.fid)

        count = get_basic_counters('download:{0}:{1}'.format(self.node, self.fid))
        assert_equal(count, (1,2))

    def test_update_counters_file_version_unique(self):
        count = get_basic_counters('download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid))
        assert_equal(count, (None,None))

        page = 'download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid)

        download_file_version_(node=self.node, fid=self.fid, vid=self.vid)
        session.data['visited'].append(page)
        download_file_version_(node=self.node, fid=self.fid, vid=self.vid)

        count = get_basic_counters('download:{0}:{1}:{2}'.format(self.node, self.fid, self.vid))
        assert_equal(count, (1,2))

    def test_get_basic_counters(self):
        page = 'node:' + str(self.node._id)

        d = {'$inc': {}}
        d['$inc']['total'] = 5
        d['$inc']['unique'] = 3

        collection.update({'_id': page}, d, True, False)
        count = get_basic_counters(page)
        assert_equal(count, (3,5))




