# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
import pytest
from mock import MagicMock

class PreprintsListFilteringMixin(object):

    def setUp(self):
        super(PreprintsListFilteringMixin, self).setUp()

        self._setUp()

        self.provider_url = '{}filter[provider]='.format(self.url)
        self.id_url = '{}filter[id]='.format(self.url)
        self.date_created_url = '{}filter[date_created]='.format(self.url)
        self.date_modified_url = '{}filter[date_modified]='.format(self.url)
        self.date_published_url = '{}filter[date_published]='.format(self.url)
        self.is_published_url = '{}filter[is_published]='.format(self.url)

    def _setUp(self):
        raise NotImplementedError

    def test_provider_filter_null(self):
        expected = []
        res = self.app.get('{}null'.format(self.provider_url), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_provider_filter_equals_returns_one(self):
        expected = [self.preprint_two._id]
        res = self.app.get('{}{}'.format(self.provider_url, self.provider_two._id), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert_equal(expected, actual)

    def test_provider_filter_equals_returns_multiple(self):
        expected = set([self.preprint._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.provider_url, self.provider._id), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
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
