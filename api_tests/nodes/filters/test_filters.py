# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
import pytest


class NodesListFilteringMixin(object):

    def setUp(self):
        super(NodesListFilteringMixin, self).setUp()

        self._setUp()

        self.parent_url = '{}filter[parent]='.format(self.url)
        self.root_url ='{}filter[root]='.format(self.url)

    def _setUp(self):
        raise NotImplementedError

    def test_parent_filter_null(self):
        expected = [self.node_A._id]
        res = self.app.get('{}null'.format(self.parent_url), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

    def test_parent_filter_equals_returns_one(self):
        expected = [self.node_C2._id]
        res = self.app.get('{}{}'.format(self.parent_url, self.node_B2._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

    def test_parent_filter_equals_returns_multiple(self):
        expected = [self.node_B1._id, self.node_B2._id]
        res = self.app.get('{}{}'.format(self.parent_url, self.node_A._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_root_filter_null(self):
        res = self.app.get('{}null'.format(self.root_url), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['parameter'], 'filter')

    def test_root_filter_equals_returns_branch(self):
        expected = [self.node_C2._id, self.node_D2._id]
        res = self.app.get('{}{}'.format(self.root_url, self.node_B2._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_root_filter_equals_returns_tree(self):
        expected = [self.node_B1._id, self.node_B2._id, self.node_C1._id, self.node_C2._id, self.node_D2._id]
        res = self.app.get('{}{}'.format(self.root_url, self.node_A._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))
