# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
import pytest

from framework.auth.core import Auth

from tests.base import ApiTestCase
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)
from website.preprints.model import PreprintService


class PreprintsListFilteringMixin(object):

    def setUp(self):
        super(PreprintsListFilteringMixin, self).setUp()
        # user defined by subclasses to allow user preprints testing in the future
        assert self.user, 'Subclasses of PreprintsListFilteringMixin must define self.user'
        assert self.provider, 'Subclasses of PreprintsListFilteringMixin must define self.provider'
        assert self.provider_two, 'Subclasses of PreprintsListFilteringMixin must define self.provider_two'
        assert self.provider_three, 'Subclasses of PreprintsListFilteringMixin must define self.provider_three'
        assert self.project, 'Subclasses of PreprintsListFilteringMixin must define self.project'
        assert self.project_two, 'Subclasses of PreprintsListFilteringMixin must define self.projec_two'
        assert self.project_three, 'Subclasses of PreprintsListFilteringMixin must define self.project_three'
        assert self.url, 'Subclasses of PreprintsListFilteringMixin must define self.url' 

        self.subject = SubjectFactory()
        self.subject_two = SubjectFactory()

        self.preprint = PreprintFactory(creator=self.user, project=self.project, provider=self.provider, subjects=[[self.subject._id]])
        self.preprint_two = PreprintFactory(creator=self.user, project=self.project_two, filename='tough.txt', provider=self.provider_two, subjects=[[self.subject_two._id]])
        self.preprint_three = PreprintFactory(creator=self.user, project=self.project_three, filename='darn.txt', provider=self.provider_three, subjects=[[self.subject._id], [self.subject_two._id]])

        self.preprint_two.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.save()

        self.preprint_three.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.is_published = False
        self.preprint_three.save()

        self.provider_url = '{}filter[provider]='.format(self.url)
        self.id_url = '{}filter[id]='.format(self.url)
        self.date_created_url = '{}filter[date_created]='.format(self.url)
        self.date_modified_url = '{}filter[date_modified]='.format(self.url)
        self.date_published_url = '{}filter[date_published]='.format(self.url)
        self.is_published_url = '{}filter[is_published]='.format(self.url)

        self.is_published_and_modified_url = '{}filter[is_published]=true&filter[date_created]=2013-12-11'.format(self.url)

    def test_provider_filter_null(self):
        expected = []
        res = self.app.get('{}null'.format(self.provider_url), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_id_filter_null(self):
        expected = []
        res = self.app.get('{}null'.format(self.id_url), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_id_filter_equals_returns_one(self):
        expected = [self.preprint_two._id]
        res = self.app.get('{}{}'.format(self.id_url, self.preprint_two._id), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_date_created_filter_equals_returns_none(self):
        expected = []
        res = self.app.get('{}{}'.format(self.date_created_url, '2015-11-15 10:09:08.070605+00:00'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_date_created_filter_equals_returns_one(self):
        expected = [self.preprint._id]
        res = self.app.get('{}{}'.format(self.date_created_url, self.preprint.date_created), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_date_created_filter_equals_returns_multiple(self):
        expected = set([self.preprint_two._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.date_created_url, self.preprint_two.date_created), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert_equal(expected, actual)

    def test_date_modified_filter_equals_returns_none(self):
        expected = []
        res = self.app.get('{}{}'.format(self.date_modified_url, '2015-11-15 10:09:08.070605+00:00'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    # This test was causing problems because modifying anything caused set modified dates to update to current date
    # This test could hypothetically fail if the time between fixture creations splits a day (e.g., midnight)
    def test_date_modified_filter_equals_returns_multiple(self):
        expected = set([self.preprint._id, self.preprint_two._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.date_modified_url, self.preprint.date_modified), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert_equal(expected, actual)

    def test_date_published_filter_equals_returns_none(self):
        expected = []
        res = self.app.get('{}{}'.format(self.date_published_url, '2015-11-15 10:09:08.070605+00:00'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_date_published_filter_equals_returns_one(self):
        expected = [self.preprint._id]
        res = self.app.get('{}{}'.format(self.date_published_url, self.preprint.date_published), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_date_published_filter_equals_returns_multiple(self):
        expected = set([self.preprint_two._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.date_published_url, self.preprint_two.date_published), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert_equal(expected, actual)

    def test_is_published_false_filter_equals_returns_one(self):
        expected = [self.preprint_three._id]
        res = self.app.get('{}{}'.format(self.is_published_url, 'false'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_is_published_true_filter_equals_returns_multiple(self):
        expected = set([self.preprint._id, self.preprint_two._id])
        res = self.app.get('{}{}'.format(self.is_published_url, 'true'), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert_equal(expected, actual)

    def test_multiple_filters_returns_one(self):
        expected = set([self.preprint_two._id])
        res = self.app.get(self.is_published_and_modified_url,
            auth=self.user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert_equal(expected, actual)
