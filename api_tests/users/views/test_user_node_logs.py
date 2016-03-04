# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from framework.auth import Auth

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory
from tests.factories import NodeFactory
from tests.factories import NodeLogFactory

from api.base.settings.defaults import API_BASE


class TestUserLogs(ApiTestCase):
    def setUp(self):
        super(TestUserLogs, self).setUp()
        self.user = AuthUserFactory()
        self.other_user = AuthUserFactory()
        self.node = NodeFactory(creator=self.user)
        self.other_node = NodeFactory(creator=self.other_user)
        self.other_node.add_contributor(self.user, auth=Auth(self.other_user))
        self.other_node.save()
        # Logs require paths here as the aggregate query assumes that a file log has a path param
        self.log = NodeLogFactory(action='osf_storage_file_added', params={'node': self.node._id, 'path': 'a_path'})
        self.log2 = NodeLogFactory(action='osf_storage_file_added', params={'node': self.other_node._id, 'path': 'another_path'})
        self.log_url = '/{0}users/{1}/logs/'.format(API_BASE, self.user._id)

    def test_retrieve_all_logs(self):
        res = self.app.get(
            self.log_url,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        node_log_ids = [node_log['id'] for node_log in res.json['data']]
        assert_true(self.log._id in node_log_ids)
        assert_true(self.log2._id in node_log_ids)

        assert_equal(res.json['links']['meta']['total'], 5)  # Node creation (x2), contributor added, custom logs (x2)

    def test_no_logs(self):
        user = AuthUserFactory()

        res = self.app.get(
            '/{0}users/{1}/logs/'.format(API_BASE, user._id),
            auth=user.auth,
            expect_errors=True
        )

        assert_equal(res.status_code, 404)

    def test_aggregates(self):
        log = NodeLogFactory(action='wiki_updated', params={'node': self.node._id})
        log2 = NodeLogFactory(action='comment_added', params={'node': self.other_node._id})
        res = self.app.get(
            self.log_url + '?aggregates=1',
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        aggregates = res.json['meta']['aggregates']
        assert_equal(aggregates['nodes'], 2)
        assert_equal(aggregates['comments'], 1)
        assert_equal(aggregates['wiki'], 1)
        assert_equal(aggregates['files'], 2)

    def test_logs_from_project_no_longer_being_contributed(self):
        self.other_node.remove_contributor(self.user, auth=Auth(self.other_user))
        res = self.app.get(
            self.log_url,
            auth=self.user.auth
        )

        assert_equal(res.status_code, 200)

        node_log_ids = [node_log['id'] for node_log in res.json['data']]
        assert_true(self.log._id in node_log_ids)
        assert_true(self.log2._id not in node_log_ids)

        assert_equal(res.json['links']['meta']['total'], 2)

    def test_no_auth(self):
        res = self.app.get(
            '/{0}users/{1}/logs/'.format(API_BASE, self.user._id),
            expect_errors=True
        )

        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'], 'Authentication credentials were not provided.')

    def test_wrong_auth(self):
        res = self.app.get(
            '/{0}users/{1}/logs/'.format(API_BASE, self.user._id),
            auth=self.other_user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, 403)
        assert_equal(res.json['errors'][0]['detail'], 'You do not have permission to perform this action.')
