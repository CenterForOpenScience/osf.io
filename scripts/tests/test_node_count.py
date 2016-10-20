import datetime
from framework.auth.core import User
from tests.base import OsfTestCase
from tests.factories import UserFactory, RegistrationFactory, ProjectFactory, WithdrawnRegistrationFactory, NodeFactory
from nose.tools import *  # PEP8 asserts
from website.project.model import Node

from scripts.analytics.node_count import get_node_count


class TestNodeCount(OsfTestCase):

    def setUp(self):
        super(TestNodeCount, self).setUp()

        self.user = UserFactory()

        # Projects
        self.public_project = ProjectFactory(is_public=True)
        self.private_project = ProjectFactory(is_public=False)
        self.other_public_project = ProjectFactory(is_public=True)

        # Registrations
        self.public_registration = RegistrationFactory(project=self.public_project)
        self.private_registration = RegistrationFactory(project=self.private_project)

        self.embargoed_registration = RegistrationFactory(project=self.other_public_project, creator=self.user)
        self.embargoed_registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.embargoed_registration.save()

        self.reg_to_be_withdrawn = RegistrationFactory(project=self.other_public_project)
        self.withdrawn_registration = WithdrawnRegistrationFactory(registration = self.reg_to_be_withdrawn, user=self.reg_to_be_withdrawn.creator)

        # Add some folders and Deleted Nodes
        self.deleted_node = NodeFactory(is_deleted=True)
        self.other_deleted_node = NodeFactory(is_deleted=True)

        self.folder = NodeFactory(is_folder=True)


    def tearDown(self):
        super(TestNodeCount, self).tearDown()
        Node.remove()
        User.remove()

    def test_get_node_count(self):
        results = get_node_count()

        nodes = results['nodes']
        assert_equal(nodes['total'], 7)
