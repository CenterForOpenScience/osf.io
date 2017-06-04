import pytz
import datetime
from framework.auth.core import User
from tests.base import OsfTestCase
from tests.factories import UserFactory, NodeLogFactory
from nose.tools import *  # PEP8 asserts
from website.project.model import Node, NodeLog

from scripts.analytics.node_log_events import NodeLogEvents


class TestNodeLogAnalytics(OsfTestCase):

    def setUp(self):
        super(TestNodeLogAnalytics, self).setUp()

        self.user_one = UserFactory()
        self.user_two = UserFactory()

        # Two node logs for user one
        self.node_log_node_created = NodeLogFactory(action='node_created', user=self.user_one)
        self.node_log_file_added = NodeLogFactory(action='file_added', user=self.user_one)

        # Two node logs for user two
        self.node_log_wiki_updated = NodeLogFactory(action='wiki_updated', user=self.user_two)
        self.node_log_project_created = NodeLogFactory(action='project_created', user=self.user_two)

        self.end_date = datetime.datetime.utcnow() - datetime.timedelta(1)

        for node_log in NodeLog.find():
            node_log.date = self.end_date - datetime.timedelta(0.1)
            node_log.save()

        self.results = NodeLogEvents().get_events(self.end_date.date())

        self.node_log_node_created.reload()
        self.node_log_file_added.reload()
        self.node_log_wiki_updated.reload()
        self.node_log_project_created.reload()

    def tearDown(self):
        super(TestNodeLogAnalytics, self).tearDown()
        Node.remove()
        User.remove()

    def test_results_structure(self):
        expected = [
            {
                'keen': {'timestamp': self.node_log_node_created.date.replace(tzinfo=pytz.UTC).isoformat()},
                'date': self.node_log_node_created.date.replace(tzinfo=pytz.UTC).isoformat(),
                'action': 'node_created',
                'user_id': self.user_one._id
            },
            {
                'keen': {'timestamp': self.node_log_file_added.date.replace(tzinfo=pytz.UTC).isoformat()},
                'date': self.node_log_file_added.date.replace(tzinfo=pytz.UTC).isoformat(),
                'action': 'file_added',
                'user_id': self.user_one._id
            },
            {
                'keen': {'timestamp': self.node_log_wiki_updated.date.replace(tzinfo=pytz.UTC).isoformat()},
                'date': self.node_log_wiki_updated.date.replace(tzinfo=pytz.UTC).isoformat(),
                'action': 'wiki_updated',
                'user_id': self.user_two._id
            },
            {
                'keen': {'timestamp': self.node_log_project_created.date.replace(tzinfo=pytz.UTC).isoformat()},
                'date': self.node_log_project_created.date.replace(tzinfo=pytz.UTC).isoformat(),
                'action': 'project_created',
                'user_id': self.user_two._id
            }
        ]

        assert_items_equal(expected, self.results)

