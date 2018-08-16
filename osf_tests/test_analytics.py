# -*- coding: utf-8 -*-
"""
Unit tests for analytics logic in framework/analytics/__init__.py
"""
import re
import unittest

import mock
import pytest
from django.utils import timezone
from nose.tools import *  # flake8: noqa  (PEP8 asserts)
from flask import Flask

from datetime import datetime

from addons.osfstorage.models import OsfStorageFile
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


@pytest.fixture()
def user():
    return UserFactory()


@pytest.fixture()
def project():
    return ProjectFactory()

@pytest.fixture()
def project_with_contrib(user):
    return ProjectFactory(creator=user)


@pytest.fixture()
def file_node(project):
    file_node = OsfStorageFile(name='test', node=project)
    file_node.save()
    return file_node

@pytest.fixture()
def file_node2(project):
    file_node2 = OsfStorageFile(name='test2', node=project)
    file_node2.save()
    return file_node2

@pytest.fixture()
def file_node3(project):
    file_node2 = OsfStorageFile(name='test3', node=project)
    file_node2.save()
    return file_node2

@pytest.fixture()
def page_counter(project, file_node):
    page_counter_id = 'download:{}:{}'.format(project._id, file_node.id)
    page_counter, created = PageCounter.objects.select_for_update().get_or_create(_id=page_counter_id)
    page_counter.date = {u'2018/02/04': {u'total': 41, u'unique': 33}}
    page_counter.save()
    return page_counter

@pytest.fixture()
def page_counter2(project, file_node2):
    page_counter_id = 'download:{}:{}'.format(project._id, file_node2.id)
    page_counter, created = PageCounter.objects.select_for_update().get_or_create(_id=page_counter_id)
    page_counter.date = {u'2018/02/04': {u'total': 4, u'unique': 26}}
    page_counter.save()
    return page_counter

@pytest.fixture()
def page_counter_for_individual_version(project, file_node3):
    page_counter_id = 'download:{}:{}:0'.format(project._id, file_node3.id)
    page_counter, created = PageCounter.objects.select_for_update().get_or_create(_id=page_counter_id)
    page_counter.date = {u'2018/02/04': {u'total': 1, u'unique': 1}}
    page_counter.save()
    return page_counter


class TestPageCounter:

    @mock.patch('osf.models.analytics.session')
    def test_download_update_counter(self, mock_session, project, file_node):
        mock_session.data = {}
        page_counter_id = 'download:{}:{}'.format(project._id, file_node.id)

        PageCounter.update_counter(page_counter_id, {})

        page_counter = PageCounter.objects.get(_id=page_counter_id)
        assert page_counter.total == 1
        assert page_counter.unique == 1

        PageCounter.update_counter(page_counter_id, {})

        page_counter.refresh_from_db()
        assert page_counter.total == 2
        assert page_counter.unique == 1

    @mock.patch('osf.models.analytics.session')
    def test_download_update_counter_contributor(self, mock_session, user, project_with_contrib, file_node):
        mock_session.data = {'auth_user_id': user._id}
        page_counter_id = 'download:{}:{}'.format(project_with_contrib._id, file_node.id)

        PageCounter.update_counter(page_counter_id, {'contributors': project_with_contrib.contributors})

        page_counter = PageCounter.objects.get(_id=page_counter_id)
        assert page_counter.total == 0
        assert page_counter.unique == 0

        PageCounter.update_counter(page_counter_id, {'contributors': project_with_contrib.contributors})

        page_counter.refresh_from_db()
        assert page_counter.total == 0
        assert page_counter.unique == 0

    def test_get_all_downloads_on_date(self, page_counter, page_counter2):
        date = datetime(2018, 2, 4)

        total_downloads = PageCounter.get_all_downloads_on_date(date)

        assert total_downloads == 45

    def test_get_all_downloads_on_date_exclude_versions(self, page_counter, page_counter2, page_counter_for_individual_version):
        date = datetime(2018, 2, 4)

        total_downloads = PageCounter.get_all_downloads_on_date(date)

        assert total_downloads == 45

    def test_download_all_versions_regex(self):
        # Checks regex to ensure we don't double count versions totals for that file node.

        match = re.match(PageCounter.DOWNLOAD_ALL_VERSIONS_ID_PATTERN, 'bad id')
        assert not match

        match = re.match(PageCounter.DOWNLOAD_ALL_VERSIONS_ID_PATTERN, 'views:guid1:fileid')
        assert not match

        match = re.match(PageCounter.DOWNLOAD_ALL_VERSIONS_ID_PATTERN, 'download:guid1:fileid:0')
        assert not match

        match = re.match(PageCounter.DOWNLOAD_ALL_VERSIONS_ID_PATTERN, 'download:guid1:fileid')
        assert match


