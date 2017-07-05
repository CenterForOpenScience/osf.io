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
        self.user_two = AuthUserFactory()

        self.node_A = ProjectFactory(creator=self.user)
        self.node_B1 = NodeFactory(parent=self.node_A, creator=self.user)
        self.node_B2 = NodeFactory(parent=self.node_A, creator=self.user)
        self.node_C1 = NodeFactory(parent=self.node_B1, creator=self.user)
        self.node_C2 = NodeFactory(parent=self.node_B2, creator=self.user)
        self.node_D2 = NodeFactory(parent=self.node_C2, creator=self.user)

        self.node_A.add_contributor(self.user_two, save=True)

        self.parent_url = '{}filter[parent]='.format(self.url)
        self.root_url ='{}filter[root]='.format(self.url)
        self.tags_url ='{}filter[tags]='.format(self.url)
        self.contributors_url ='{}filter[contributors]='.format(self.url)

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

    def test_tag_filter(self):
        self.node_A.add_tag('nerd', auth=Auth(self.node_A.creator), save=True)
        expected = [self.node_A._id]
        res = self.app.get('{}nerd'.format(self.tags_url), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

        res = self.app.get('{}bird'.format(self.tags_url), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal([], actual)

    def test_contributor_filter(self):
        expected = [self.node_A._id]
        res = self.app.get('{}{}'.format(self.contributors_url, self.user_two._id), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)


class NodesListDateFilteringMixin(object):

    def setUp(self):
        super(NodesListDateFilteringMixin, self).setUp()

        assert self.url, 'Subclasses of NodesListDateFilteringMixin must define self.url'

        self.user = AuthUserFactory()

        self.node_may = ProjectFactory(creator=self.user)
        self.node_june = ProjectFactory(creator=self.user)
        self.node_july = ProjectFactory(creator=self.user)

        self.node_may.date_created = '2016-05-01 00:00:00.000000+00:00'
        self.node_june.date_created = '2016-06-01 00:00:00.000000+00:00'
        self.node_july.date_created = '2016-07-01 00:00:00.000000+00:00'

        self.node_may.save()
        self.node_june.save()
        self.node_july.save()

        self.date_created_url = '{}filter[date_created]='.format(self.url)

    def test_date_filter_equals(self):
        expected = []
        res = self.app.get('{}{}'.format(self.date_created_url, '2016-04-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

        expected = [self.node_may._id]
        res = self.app.get('{}{}'.format(self.date_created_url, self.node_may.date_created), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

    def test_date_filter_gt(self):
        url = '{}filter[date_created][gt]='.format(self.url)

        expected = []
        res = self.app.get('{}{}'.format(url, '2016-08-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

        expected = [self.node_june._id, self.node_july._id]
        res = self.app.get('{}{}'.format(url, '2016-05-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_date_filter_gte(self):
        url = '{}filter[date_created][gte]='.format(self.url)

        expected = []
        res = self.app.get('{}{}'.format(url, '2016-08-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

        expected = [self.node_may._id, self.node_june._id, self.node_july._id]
        res = self.app.get('{}{}'.format(url, '2016-05-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_date_fitler_lt(self):
        url = '{}filter[date_created][lt]='.format(self.url)

        expected = []
        res = self.app.get('{}{}'.format(url, '2016-05-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

        expected = [self.node_may._id, self.node_june._id]
        res = self.app.get('{}{}'.format(url, '2016-07-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_date_filter_lte(self):
        url = '{}filter[date_created][lte]='.format(self.url)

        expected = []
        res = self.app.get('{}{}'.format(url, '2016-04-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

        expected = [self.node_may._id, self.node_june._id, self.node_july._id]
        res = self.app.get('{}{}'.format(url, '2016-07-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(set(expected), set(actual))

    def test_date_filter_eq(self):
        url = '{}filter[date_created][eq]='.format(self.url)

        expected = []
        res = self.app.get('{}{}'.format(url, '2016-04-01'), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)

        expected = [self.node_may._id]
        res = self.app.get('{}{}'.format(url, self.node_may.date_created), auth=self.user.auth)
        actual = [node['id'] for node in res.json['data']]
        assert_equal(expected, actual)
