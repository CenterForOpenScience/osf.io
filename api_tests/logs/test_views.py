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
from website.project import new_dashboard

from api.base.settings.defaults import API_BASE


class LogsTestCase(ApiTestCase):

    def setUp(self):
        super(LogsTestCase, self).setUp()

        self.user = AuthUserFactory()

        self.action_set = NodeLog.actions
        self.node = ProjectFactory(is_public=False)
        for i in range(len(self.action_set)):
            self.node.add_log(
                self.action_set[i],
                {},
                Auth(self.node.creator),
                save=True
            )
        self.node.add_contributor(self.user, permissions=[osf_permissions.READ], auth=Auth(self.node.creator), log=False, save=True)
        self.node_log_url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        self.url = '/{}logs/'.format(API_BASE)

        self.public_node = ProjectFactory(is_public=True)
        for i in range(len(self.action_set)):
            self.public_node.add_log(
                self.action_set[i],
                {},
                Auth(self.public_node.creator),
                save=True
            )

    def tearDown(self):
        NodeLog.remove()
        Node.remove()


class TestLogNodeList(LogsTestCase):
    def test_log_nodes_invalid_log_gets_404(self):
        res = self.app.get(self.url + '/abcdef/nodes/', expect_errors=True)
        assert_equal(res.status_code, http.NOT_FOUND)

    def test_log_detail_returns_data(self):
        test_log = self.node.logs[0]
        url = self.url + '{}/'.format(test_log._id)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        json_data = res.json['data']
        assert_equal(json_data['id'], test_log._id)