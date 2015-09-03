# -*- coding: utf-8 -*-
from nose.tools import *  # noqa

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory
)

from framework.auth.core import Auth

from website.models import NodeLog

from api.base.settings.defaults import API_BASE

class LogsTestCase(ApiTestCase):

    def setUp(self):
        super(LogsTestCase, self).setUp()

        self.user = AuthUserFactory()

        self.action_set = NodeLog.actions()
        self.node = ProjectFactory()
        for i in range(len(self.action_set)):
            self.node.add_log(
                self.action_set[i],
                {},
                Auth(self.node.creator),
                save=True
            )
        self.node.add_contributor(self.user, permissions='read', auth=Auth(self.node.creator), log=False, save=True)

        self.public_node = ProjectFactory(is_public=True)
        for i in range(len(self.action_set)):
            self.public_node.add_log(
                self.action_set[i],
                {},
                Auth(self.public_node.creator),
                save=True
            )


class TestLogList(LogsTestCase):

    url = '/{}logs/'.format(API_BASE)

    def test_returns_only_public_logs_for_logged_out_user(self):        
        res = self.app.get(self.url)
        meta = res.json['links']['meta']
        assert_equal(meta['total'], len(self.action_set) + 1)

    def test_returns_public_and_contributed_logs_for_logged_in_user(self):
        res = self.app.get(self.url, auth=self.user)
        meta = res.json['links']['meta']
        assert_equal(meta['total'], 2 * (len(self.action_set) + 1))


class TestLogNodeList(LogsTestCase):

    url = '/{}logs/'.format(API_BASE)

    def test_nodes_link(self):
        self.node.add_log(self.action_set[0], {}, Auth(self.node.creator), save=True)
        log = self.node.logs[-1]
        self.public_node.logs.append(log)
        self.public_node.save()
        res = self.app.get(self.url, auth=self.user)
        data = res.json['data']
        nodes_link = data[0]['links']['nodes']['related']
        res = self.app.get(nodes_link, auth=self.user)
        meta = res.json['links']['meta']
        data = res.json['data']
        assert_equal(meta['total'], 2)
        for node in data:
            assert_in(node['id'], [self.node._id, self.public_node._id])
