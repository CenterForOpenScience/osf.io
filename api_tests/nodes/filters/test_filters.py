# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
import pytest

from osf.utils.auth import Auth

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    NodeRelationFactory,
    ProjectFactory,
)

class NodesListFilteringMixin(object):

    def setUp(self):
        super(NodesListFilteringMixin, self).setUp()

        assert self.url, 'Subclasses of NodesListFilteringMixin must define self.url'

        self.user = AuthUserFactory()

        self.node_A = ProjectFactory(creator=self.user)
        self.node_B1 = NodeFactory(parent=self.node_A, creator=self.user)
        self.node_B2 = NodeFactory(parent=self.node_A, creator=self.user)
        self.node_C1 = NodeFactory(parent=self.node_B1, creator=self.user)
        self.node_C2 = NodeFactory(parent=self.node_B2, creator=self.user)
        self.node_D2 = NodeFactory(parent=self.node_C2, creator=self.user)

        self.parent_url = '{}filter[parent]='.format(self.url)
        self.root_url ='{}filter[root]='.format(self.url)

    def test_parent_filter_null(self):
        expected = [self.node_A._id]
        res = self.app.get('{}null'.format(self.parent_url), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

    def test_parent_filter_excludes_linked_nodes(self):
        linked_node = NodeFactory()
        self.node_A.add_node_link(linked_node, auth=Auth(self.user))
        expected = [self.node_B1._id, self.node_B2._id]
        res = self.app.get('{}{}'.format(self.parent_url, self.node_A._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_not_in(linked_node._id, actual)
        assert_equal(set(expected), set(actual))

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
        expected = []
        res = self.app.get('{}{}'.format(self.root_url, self.node_B2._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

    def test_root_filter_equals_returns_tree(self):
        expected = [self.node_A._id, self.node_B1._id, self.node_B2._id, self.node_C1._id, self.node_C2._id, self.node_D2._id]
        res = self.app.get('{}{}'.format(self.root_url, self.node_A._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))
