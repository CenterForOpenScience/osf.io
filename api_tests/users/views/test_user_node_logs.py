# -*- coding: utf-8 -*-
import urlparse
from nose.tools import *  # flake8: noqa

from framework.auth import Auth

from tests.base import ApiTestCase
from tests.factories import AuthUserFactory
from tests.factories import NodeFactory
from tests.factories import NodeLogFactory

from api.base.settings.defaults import API_BASE


class TestUserNodeLogs(ApiTestCase):
    def setUp(self):
        super(TestUserNodeLogs, self).setUp()
        self.user = AuthUserFactory()
        self.other_user = AuthUserFactory
        self.node = NodeFactory(creator=self.user)
        self.other_node = NodeFactory(creator=self.other_user)
        self.other_node.add_contributor(self.user, auth=Auth(self.other_user))
        self.log = NodeLogFactory(params={'node': self.node._id})
        self.log2 = NodeLogFactory(params={'node': self.other_node._id})
        self.log_url = '/{0}users/{1}/node_logs/'.format(API_BASE, self.user._id)

    def test_retrieve_all_logs(self):
        pass

    def test_no_logs(self):
        pass

    def test_aggregates(self):
        pass

    def test_logs_from_contrib_nodes(self):
        pass

    def test_logs_from_project_no_longer_being_contributed(self):
        pass

    def test_no_auth(self):
        pass
