# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa
import pytest

from osf.models import Node

from osf_tests.factories import (
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationFactory,
)


class RegistrationListFilteringMixin(object):

    def setUp(self):
        super(RegistrationListFilteringMixin, self).setUp()

        assert self.url, 'Subclasses of RegistrationListFilteringMixin must define self.url'

        self.user = AuthUserFactory()

        self.A = ProjectFactory(creator=self.user)
        self.B1 = NodeFactory(parent=self.A, creator=self.user)
        self.B2 = NodeFactory(parent=self.A, creator=self.user)
        self.C1 = NodeFactory(parent=self.B1, creator=self.user)
        self.C2 = NodeFactory(parent=self.B2, creator=self.user)
        self.D2 = NodeFactory(parent=self.C2, creator=self.user)

        self.node_A = RegistrationFactory(project=self.A, creator=self.user)
        self.node_B2 = RegistrationFactory(project=self.B2, creator=self.user)

        self.parent_url = '{}filter[parent]='.format(self.url)
        self.root_url ='{}filter[root]='.format(self.url)

    def test_parent_filter_null(self):
        expected = [self.node_A._id, self.node_B2._id]
        res = self.app.get('{}null'.format(self.parent_url), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_parent_filter_equals_returns_one(self):
        expected = [n._id for n in self.node_B2.get_nodes()]
        res = self.app.get('{}{}'.format(self.parent_url, self.node_B2._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(len(actual), 1)
        assert_equal(expected, actual)

    def test_parent_filter_equals_returns_multiple(self):
        expected = [n._id for n in self.node_A.get_nodes()]
        res = self.app.get('{}{}'.format(self.parent_url, self.node_A._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(len(actual), 2)
        assert_equal(set(expected), set(actual))

    def test_root_filter_null(self):
        res = self.app.get('{}null'.format(self.root_url), auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)
        assert_equal(res.json['errors'][0]['source']['parameter'], 'filter')

    def test_root_filter_equals_returns_branch(self):
        expected = [n._id for n in Node.objects.get_children(self.node_B2)]
        expected.append(self.node_B2._id)
        res = self.app.get('{}{}'.format(self.root_url, self.node_B2._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_root_filter_equals_returns_tree(self):
        expected = [n._id for n in Node.objects.get_children(self.node_A)]
        expected.append(self.node_A._id)
        res = self.app.get('{}{}'.format(self.root_url, self.node_A._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(len(actual), 6)
        assert_equal(set(expected), set(actual))
