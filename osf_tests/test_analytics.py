# -*- coding: utf-8 -*-
"""
Unit tests for analytics logic in framework/analytics/__init__.py
"""

import mock
import pytest
from django.utils import timezone
from nose.tools import *  # noqa: F403

from datetime import datetime

from addons.osfstorage.models import OsfStorageFile
from framework import analytics
from osf.models import PageCounter, OSFGroup

from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, ProjectFactory


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
def project(user):
    return ProjectFactory(creator=user)

@pytest.fixture()
def file_node(project):
    file_node = OsfStorageFile(name='test', target=project)
    file_node.save()
    return file_node

@pytest.fixture()
def file_node2(project):
    file_node2 = OsfStorageFile(name='test2', target=project)
    file_node2.save()
    return file_node2

@pytest.fixture()
def file_node3(project):
    file_node3 = OsfStorageFile(name='test3', target=project)
    file_node3.save()
    return file_node3

@pytest.fixture()
def page_counter(project, file_node):
    page_counter_id = 'download:{}:{}'.format(project._id, file_node.id)
    resource = project.guids.first()
    page_counter, created = PageCounter.objects.get_or_create(_id=page_counter_id, resource=resource, file=file_node, version=None, action='download', date={u'2018/02/04': {u'total': 41, u'unique': 33}})
    return page_counter

@pytest.fixture()
def page_counter2(project, file_node2):
    page_counter_id = 'download:{}:{}'.format(project._id, file_node2.id)
    resource = project.guids.first()
    page_counter, created = PageCounter.objects.get_or_create(_id=page_counter_id, resource=resource, file=file_node2, version=None, action='download', date={u'2018/02/04': {u'total': 4, u'unique': 26}})
    return page_counter

@pytest.fixture()
def page_counter_for_individual_version(project, file_node3):
    page_counter_id = 'download:{}:{}'.format(project._id, file_node3.id)
    resource = project.guids.first()
    page_counter, created = PageCounter.objects.get_or_create(_id=page_counter_id, resource=resource, file=file_node3, version=0, action='download', date={u'2018/02/04': {u'total': 1, u'unique': 1}})
    return page_counter


@pytest.mark.django_db
class TestPageCounter:

    @mock.patch('osf.models.analytics.session')
    def test_download_update_counter(self, mock_session, project, file_node):
        mock_session.data = {}
        resource = project.guids.first()
        PageCounter.update_counter(resource, file_node, version=None, action='download', node_info={})

        page_counter = PageCounter.objects.get(resource=resource, file=file_node, version=None, action='download')
        assert page_counter.total == 1
        assert page_counter.unique == 1

        PageCounter.update_counter(resource, file_node, version=None, action='download', node_info={})

        page_counter.refresh_from_db()
        assert page_counter.total == 2
        assert page_counter.unique == 1

    @mock.patch('osf.models.analytics.session')
    def test_download_update_counter_contributor(self, mock_session, user, project, file_node):
        mock_session.data = {'auth_user_id': user._id}
        resource = project.guids.first()

        PageCounter.update_counter(resource, file_node, version=None, action='download', node_info={'contributors': project.contributors})

        page_counter = PageCounter.objects.get(resource=resource, file=file_node, version=None, action='download')
        assert page_counter.total == 0
        assert page_counter.unique == 0

        PageCounter.update_counter(resource, file_node, version=None, action='download', node_info={'contributors': project.contributors})

        page_counter.refresh_from_db()
        assert page_counter.total == 0
        assert page_counter.unique == 0

        platform_group = OSFGroup.objects.create(creator=user, name='Platform')
        group_member = UserFactory()
        project.add_osf_group(platform_group)

        mock_session.data = {'auth_user_id': group_member._id}
        PageCounter.update_counter(resource, file_node, version=None, action='download', node_info={
            'contributors': project.contributors_and_group_members}
        )
        page_counter.refresh_from_db()
        assert page_counter.total == 1
        assert page_counter.unique == 1

        platform_group.make_member(group_member)
        PageCounter.update_counter(resource, file_node, version=None, action='download', node_info={
            'contributors': project.contributors_and_group_members}
        )
        assert page_counter.total == 1
        assert page_counter.unique == 1

    def test_get_all_downloads_on_date(self, page_counter, page_counter2):
        """
        This method tests that multiple pagecounter objects have their download totals summed properly.

        :param page_counter: represents a page_counter for a file node being downloaded
        :param page_counter2: represents a page_counter for another file node being downloaded
        """

        date = datetime(2018, 2, 4)

        total_downloads = PageCounter.get_all_downloads_on_date(date)

        assert total_downloads == 45

    def test_get_all_downloads_on_date_exclude_versions(self, page_counter, page_counter2, page_counter_for_individual_version):
        """
        This method tests that individual version counts for file node's aren't "double counted" in the totals
        for a page counter. We don't add the file node's total to the versions total.

        :param page_counter: represents a page_counter for a file node being downloaded
        :param page_counter2: represents a page_counter for another file node being downloaded
        """
        date = datetime(2018, 2, 4)

        total_downloads = PageCounter.get_all_downloads_on_date(date)

        assert total_downloads == 45
