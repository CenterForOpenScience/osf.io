# -*- coding: utf-8 -*-
import httplib as http

from nose.tools import *  # noqa

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory
)

from framework.auth.core import Auth

from website.models import NodeLog, Node
from website.util import permissions as osf_permissions
from api.base.settings.defaults import API_BASE


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
        self.public_node.add_contributor(self.user, permissions=[osf_permissions.READ], auth=Auth(self.node.creator), log=True, save=True)

        self.public_log = self.public_node.logs[0]
        self.public_log_add_contributor = self.public_node.logs[1]

        self.node_log_url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        self.url = '/{}logs/'.format(API_BASE)
        self.log_nodes_url = self.url + '{}/nodes/'.format(self.log._id)
        self.private_log_detail = self.url + '{}/'.format(self.log._id)
        self.log_public_nodes_url = self.url + '{}/nodes/'.format(self.public_log._id)
        self.public_log_detail = self.url + '{}/'.format(self.public_log._id)
        self.private_log_contribs_url = self.url + '{}/contributors/'.format(self.log_add_contributor._id)
        self.public_log_contribs_url = self.url + '{}/contributors/'.format(self.public_log_add_contributor._id)

    def tearDown(self):
        NodeLog.remove()
        Node.remove()


class TestLogNodeList(LogsTestCase):

    def test_log_nodes_invalid_log_gets_404(self):
        res = self.app.get(self.url + '/abcdef/nodes/', expect_errors=True)
        assert_equal(res.status_code, http.NOT_FOUND)

    def test_log_private_nodes_list_logged_out_user_cannot_access_logs(self):
        res = self.app.get(self.log_nodes_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_log_private_nodes_list_logged_in_contributor_can_access_logs(self):
        res = self.app.get(self.log_nodes_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.node._id)

    def test_log_private_nodes_list_logged_in_non_contributor_cannot_access_logs(self):
        res = self.app.get(self.log_nodes_url, auth=self.user_two.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    def test_log_public_nodes_logged_in_contributor_can_access_logs(self):
        res = self.app.get(self.log_public_nodes_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.public_node._id)

    def test_log_public_nodes_logged_in_non_contributor_can_access_logs(self):
        res = self.app.get(self.log_public_nodes_url, auth=self.user_two.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['id'], self.public_node._id)

