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

        self.action_set = NodeLog.actions()
        self.node = ProjectFactory(is_public=False)
        for i in range(len(self.action_set)):
            self.node.add_log(
                self.action_set[i],
                {},
                Auth(self.node.creator),
                save=True
            )
        self.node.add_contributor(self.user, permissions=[osf_permissions.READ], auth=Auth(self.node.creator), log=False, save=True)

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


class TestLogList(LogsTestCase):

    url = '/{}logs/'.format(API_BASE)

    def test_returns_only_public_logs_for_logged_out_user(self):
        res = self.app.get(self.url)
        meta = res.json['links']['meta']
        assert_equal(meta['total'], len(self.action_set) + 1)

        private_log_ids = [l._id for l in self.node.logs]
        for log in res.json['data']:
            assert_not_in(log['id'], private_log_ids)

    def test_returns_public_and_contributed_logs_for_logged_in_user(self):
        res = self.app.get(self.url, auth=self.user.auth)
        meta = res.json['links']['meta']
        assert_equal(meta['total'], 2 * (len(self.action_set) + 1))

    def test_returns_logs_for_admin_visible_children(self):
        self.node.set_permissions(self.user, [
            osf_permissions.READ, osf_permissions.WRITE, osf_permissions.ADMIN
        ], save=True)
        c1 = ProjectFactory(parent=self.node, is_public=False)
        c1.add_log(self.action_set[0], {}, Auth(c1.creator), save=True)
        child_logs = c1.logs

        res = self.app.get(self.url, auth=self.user.auth)
        data = res.json['data']

        returned_log_ids = [log['id'] for log in data]
        for log in child_logs:
            assert_in(log._id, returned_log_ids)


class TestLogNodeList(LogsTestCase):

    url = '/{}logs/'.format(API_BASE)

    def test_nodes_link(self):
        self.node.add_log(self.action_set[0], {}, Auth(self.node.creator), save=True)
        log = self.node.logs[-1]
        self.public_node.logs.append(log)
        self.public_node.save()
        res = self.app.get(self.url, auth=self.user)
        data = res.json['data']
        nodes_link = data[0]['relationships']['nodes']['links']['url']['href']
        res = self.app.get(nodes_link, auth=self.user.auth)
        meta = res.json['links']['meta']
        data = res.json['data']
        assert_equal(meta['total'], 2)
        for node in data:
            assert_in(node['id'], [self.node._id, self.public_node._id])

    def test_log_nodes_list_filters_nodes_user_can_not_see(self):
        private_node = ProjectFactory()
        log = self.node.logs[0]
        log.node__logged.append(private_node)
        log.save()

        res = self.app.get(self.url + '{0}/nodes/'.format(log._id))
        assert_equal(len(res.json['data']), len(log.node__logged) - 1)

    def test_log_nodes_invalid_log_gets_404(self):
        res = self.app.get(self.url + '/abcdef/nodes/', expect_errors=True)
        assert_equal(res.status_code, http.NOT_FOUND)

    def test_folder_node_logs_not_included(self):
        user = self.node.creator
        dash = new_dashboard(user)
        dash_logs = [l._id for l in dash.logs]
        res = self.app.get(self.url, auth=self.user)
        for log in res.json['data']:
            assert_not_in(log['id'], dash_logs)
