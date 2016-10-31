# -*- coding: utf-8 -*-
"""
Unit tests for analytics logic in framework/analytics/__init__.py
"""

import unittest

import pytest
from django.utils import timezone
from nose.tools import *  # flake8: noqa  (PEP8 asserts)
from flask import Flask

from datetime import datetime

from framework import analytics, sessions
from framework.sessions import session
from osf.models import PageCounter

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, ProjectFactory

pytestmark = pytest.mark.django_db

class TestAnalytics(OsfTestCase):

    def test_get_total_activity_count(self):
        user = UserFactory()
        date = timezone.now()

        assert_equal(analytics.get_total_activity_count(user._id), 0)
        assert_equal(analytics.get_total_activity_count(user._id), user.get_activity_points(db=None))

        analytics.increment_user_activity_counters(user._id, 'project_created', date.isoformat(), db=None)

        assert_equal(analytics.get_total_activity_count(user._id, db=None), 1)
        assert_equal(analytics.get_total_activity_count(user._id, db=None), user.get_activity_points(db=None))

    def test_increment_user_activity_counters(self):
        user = UserFactory()
        date = timezone.now()

        assert_equal(user.get_activity_points(db=None), 0)
        analytics.increment_user_activity_counters(user._id, 'project_created', date.isoformat(), db=None)
        assert_equal(user.get_activity_points(db=None), 1)


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
        self.userid = 'test123'
        self.node_info = {
            'contributors': ['test123', 'test234']
        }

    def test_update_counters_file(self):
        @analytics.update_counters('download:{target_id}:{fid}', db=None)
        def download_file_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (None, None))

        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (1, 1))

        page = 'download:{0}:{1}'.format(self.node._id, self.fid)

        session.data['visited'].append(page)
        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (1, 2))

    def test_update_counters_file_user_is_contributor(self):
        @analytics.update_counters('download:{target_id}:{fid}', db=None, node_info=self.node_info)
        def download_file_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (None, None))

        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (1, 1))

        page = 'download:{0}:{1}'.format(self.node._id, self.fid)

        session.data['visited'].append(page)
        session.data['auth_user_id'] = self.userid
        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (1, 1))

    def test_update_counters_file_user_is_not_contributor(self):
        @analytics.update_counters('download:{target_id}:{fid}', db=None, node_info=self.node_info)
        def download_file_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (None, None))

        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (1, 1))

        page = 'download:{0}:{1}'.format(self.node._id, self.fid)

        session.data['visited'].append(page)
        session.data['auth_user_id'] = "asv12uey821vavshl"
        download_file_(node=self.node, fid=self.fid)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, self.fid), db=None)
        assert_equal(count, (1, 2))

    def test_update_counters_file_version(self):
        @analytics.update_counters('download:{target_id}:{fid}:{vid}', db=None)
        def download_file_version_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        count = analytics.get_basic_counters('download:{0}:{1}:{2}'.format(self.node._id, self.fid, self.vid), db=None)
        assert_equal(count, (None, None))

        download_file_version_(node=self.node, fid=self.fid, vid=self.vid)

        count = analytics.get_basic_counters('download:{0}:{1}:{2}'.format(self.node._id, self.fid, self.vid), db=None)
        assert_equal(count, (1, 1))

        page = 'download:{0}:{1}:{2}'.format(self.node._id, self.fid, self.vid)

        session.data['visited'].append(page)
        download_file_version_(node=self.node, fid=self.fid, vid=self.vid)

        count = analytics.get_basic_counters('download:{0}:{1}:{2}'.format(self.node._id, self.fid, self.vid), db=None)
        assert_equal(count, (1, 2))

    def test_get_basic_counters(self):
        page = 'node:' + str(self.node._id)
        PageCounter.objects.create(_id=page, total=5, unique=3)

        count = analytics.get_basic_counters(page, db=None)
        assert_equal(count, (3, 5))

    @unittest.skip('Reverted the fix for #2281. Unskip this once we use GUIDs for keys in the download counts collection')
    def test_update_counters_different_files(self):
        # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/2281
        @analytics.update_counters('download:{target_id}:{fid}', db=None)
        def download_file_(**kwargs):
            return kwargs.get('node') or kwargs.get('project')

        fid1 = 'test.analytics.py'
        fid2 = 'test_analytics.py'

        download_file_(node=self.node, fid=fid1)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, fid1), db=None)
        assert_equal(count, (1, 1))
        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, fid2), db=None)
        assert_equal(count, (None, None))

        page = 'download:{0}:{1}'.format(self.node._id, fid1)

        session.data['visited'].append(page)
        download_file_(node=self.node, fid=fid1)
        download_file_(node=self.node, fid=fid2)

        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, fid1), db=None)
        assert_equal(count, (1, 2))
        count = analytics.get_basic_counters('download:{0}:{1}'.format(self.node._id, fid2), db=None)
        assert_equal(count, (1, 1))
