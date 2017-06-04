# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory,
    NodeFactory,
)

from framework.auth.core import Auth

from website.models import NodeLog, Node
from website.util import permissions as osf_permissions
from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils


class LogsTestCase(ApiTestCase):

    def setUp(self):
        super(LogsTestCase, self).setUp()

        self.user = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.action_set = NodeLog.actions
        self.node = ProjectFactory(is_public=False)

        self.node.add_contributor(self.user, permissions=[osf_permissions.READ], auth=Auth(self.node.creator), log=True, save=True)

        self.log = self.node.logs[0]
        self.log_add_contributor = self.node.logs[1]

        self.public_node = ProjectFactory(is_public=True)
        self.public_node.add_contributor(self.user, permissions=[osf_permissions.READ], auth=Auth(self.public_node.creator), log=True, save=True)

        self.public_log = self.public_node.logs[0]
        self.public_log_add_contributor = self.public_node.logs[1]

        self.node_log_url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        self.url = '/{}logs/'.format(API_BASE)
        self.log_nodes_url = self.url + '{}/nodes/'.format(self.log._id)
        self.private_log_detail = self.url + '{}/'.format(self.log._id)
        self.log_public_nodes_url = self.url + '{}/nodes/'.format(self.public_log._id)
        self.public_log_detail = self.url + '{}/'.format(self.public_log._id)

    def tearDown(self):
        NodeLog.remove()
        Node.remove()


class TestLogDetail(LogsTestCase):

    def test_log_detail_returns_data(self):
        res = self.app.get(self.private_log_detail, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data['id'], self.log._id)

    def test_log_detail_private_not_logged_in_cannot_access_logs(self):
        res = self.app.get(self.private_log_detail, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_log_detail_private_non_contributor_cannot_access_logs(self):
        res = self.app.get(self.private_log_detail, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_log_detail_public_not_logged_in_can_access_logs(self):
        res = self.app.get(self.public_log_detail, expect_errors=True)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data['id'], self.public_log._id)

    def test_log_detail_public_non_contributor_can_access_logs(self):
        res = self.app.get(self.public_log_detail, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data['id'], self.public_log._id)

    def test_log_detail_data_format_api(self):
        res = self.app.get(self.public_log_detail + '?format=api', auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_in(self.public_log._id, unicode(res.body, 'utf-8'))


class TestNodeFileLogDetail(ApiTestCase):

    def setUp(self):
        super(TestNodeFileLogDetail, self).setUp()

        self.user_one = AuthUserFactory()
        self.user_two = AuthUserFactory()

        self.node = ProjectFactory(creator=self.user_one)
        self.node.add_contributor(self.user_two)

        self.component = NodeFactory(parent=self.node, creator=self.user_one)

        self.file = api_utils.create_test_file(node=self.component, user=self.user_one)

        self.node.add_log(
            'osf_storage_file_moved',
            auth=Auth(self.user_one),
            params={
                'node': self.node._id,
                'project': self.node.parent_id,
                'path': self.file.materialized_path,
                'source': {
                    'materialized': self.file.materialized_path,
                    'addon': 'osfstorage',
                    'node': {
                        '_id': self.component._id,
                        'url': self.component.url,
                        'title': self.component.title,
                    }
                },
                'destination': {
                    'materialized': self.file.materialized_path,
                    'addon': 'osfstorage',
                    'node': {
                        '_id': self.node._id,
                        'url': self.node.url,
                        'title': self.node.title,
                    }
                }
            },
        )

        self.node.save()

        self.node_logs_url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        self.component_logs_url = '/{}nodes/{}/logs/'.format(API_BASE, self.component._id)

    def test_title_not_hidden_from_contributor_in_file_move(self):
        res = self.app.get(self.node_logs_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['attributes']['params']['destination']['node_title'], self.node.title)

    def test_title_hidden_from_non_contributor_in_file_move(self):
        res = self.app.get(self.node_logs_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_not_in(self.component.title, res.json['data'])
        assert_equal(res.json['data'][0]['attributes']['params']['source']['node_title'], 'Private Component')
