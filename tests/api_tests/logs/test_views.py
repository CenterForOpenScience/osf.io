# -*- coding: utf-8 -*-
from nose.tools import *  # noqa

from website.models import NodeLog, Node
from framework.auth.core import Auth
from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    AuthUserFactory
)

class TestLogList(ApiTestCase):

    def setUp(self):
        super(TestLogList, self).setUp()

        self.user = AuthUserFactory()
        self.url = '/{}logs/'.format(API_BASE)

        self.action_set = NodeLog.actions()
        node = ProjectFactory()
        for i in range(len(self.action_set)):
            node.add_log(
                self.action_set[i],
                {},
                Auth(node.creator),
                save=True
            )
        node.add_contributor(self.user, permissions='read', auth=Auth(node.creator), log=False, save=True)

        self.public_node = ProjectFactory(is_public=True)
        for i in range(len(self.action_set)):
            self.public_node.add_log(
                self.action_set[i],
                {},
                Auth(node.creator),
                save=True
            )

    def test_returns_only_public_logs_for_logged_out_user(self):
        res = self.app.get(self.url)
        data = res.json['data']
        meta = res.json['links']['meta']
        assert_equal(meta['total'], len(self.action_set) + 1)
        for log in data:
            assert_equal(log['nodes_logged'][0], self.public_node._id)

    def test_returns_public_and_contributed_logs_for_logged_in_user(self):
        res = self.app.get(self.url, auth=self.user)
        data = res.json['data']
        meta = res.json['links']['meta']
        assert_equal(meta['total'], 2 * (len(self.action_set) + 1))
        for log in data:
            assert_true(Node.load(log['nodes_logged'][0]).can_view(self.user))
