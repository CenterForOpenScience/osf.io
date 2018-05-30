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
from osf.models import PageCounter, Session

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, ProjectFactory

pytestmark = pytest.mark.django_db

class TestAnalytics(OsfTestCase):

    def test_get_total_activity_count(self):
        user = UserFactory()
        date = timezone.now()

        assert_equal(analytics.get_total_activity_count(user._id), 0)
        assert_equal(analytics.get_total_activity_count(user._id), user.get_activity_points())

        analytics.increment_user_activity_counters(user._id, 'project_created', date.isoformat())

        assert_equal(analytics.get_total_activity_count(user._id), 1)
        assert_equal(analytics.get_total_activity_count(user._id), user.get_activity_points())

    def test_increment_user_activity_counters(self):
        user = UserFactory()
        date = timezone.now()

        assert_equal(user.get_activity_points(), 0)
        analytics.increment_user_activity_counters(user._id, 'project_created', date.isoformat())
        assert_equal(user.get_activity_points(), 1)
