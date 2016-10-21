import datetime
from framework.auth.core import User
from tests.base import OsfTestCase
from tests.factories import UserFactory, RegistrationFactory, ProjectFactory, WithdrawnRegistrationFactory, NodeFactory
from nose.tools import *  # PEP8 asserts
from website.project.model import Node

from scripts.analytics.node_logs import get_node_log_events


class TestNodeLogAnalytics(OsfTestCase):

    def setUp(self):
        super(TestNodeLogAnalytics, self).setUp()

        self.user = UserFactory()

        self.public_project = ProjectFactory(is_public=True)
        self.private_project = ProjectFactory(is_public=False)
        self.private_component = ProjectFactory(parent=self.private_project)

        self.results = get_node_log_events(end_date=datetime.datetime.now())


    def tearDown(self):
        super(TestNodeLogAnalytics, self).tearDown()
        Node.remove()
        User.remove()

    def test_log_format(self):

        assert_equal(len(self.results), 3)
