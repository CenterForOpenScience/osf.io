from nose import tools as nt
from datetime import timedelta

from tests.base import AdminTestCase
from tests.factories import NodeFactory, RegistrationFactory

from website.project.model import Node

from admin.metrics.utils import get_projects


class TestMetricsGetProjects(AdminTestCase):
    def setUp(self):
        super(TestMetricsGetProjects, self).setUp()
        Node.remove()
        self.node = NodeFactory(
            category='project', is_public=True)  # makes 2 nodes bc category
        self.reg = RegistrationFactory()  # makes 2 nodes
        self.node_2 = NodeFactory()

    def test_get_all_nodes(self):
        count = get_projects()
        nt.assert_equal(count, 5)

    def test_get_public_nodes(self):
        count = get_projects(public=True)
        nt.assert_equal(count, 1)

    def test_get_registrations(self):
        count = get_projects(registered=True)
        nt.assert_equal(count, 1)

    def test_time(self):
        time = self.node.date_created - timedelta(seconds=1)
        count = get_projects(time=time)
        nt.assert_equal(count, 0)
