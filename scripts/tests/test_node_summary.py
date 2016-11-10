import datetime
from framework.transactions.context import TokuTransaction
from framework.auth.core import User
from framework.mongo import database
from tests.base import OsfTestCase
from tests.factories import UserFactory, RegistrationFactory, ProjectFactory, WithdrawnRegistrationFactory
from nose.tools import *  # PEP8 asserts
from website.project.model import Node

from scripts.analytics.node_summary import NodeSummary


def modify_node_dates_in_mongo(new_date):
    with TokuTransaction():
        for node in database.node.find():
            database['node'].find_and_modify(
                {'_id': node['_id']},
                {'$set': {
                    'date_created': new_date
                }}
            )

class TestNodeCount(OsfTestCase):

    def setUp(self):
        super(TestNodeCount, self).setUp()

        self.user = UserFactory()

        # 3 Projects - Public, Private, Private Component
        self.public_project = ProjectFactory(is_public=True)
        self.private_project = ProjectFactory(is_public=False)
        self.private_component = ProjectFactory(parent=self.private_project)

        # 5 Registrations - Public, Public Registrations of Private Proj + Component, Embargoed, Withdrawn
        self.public_registration = RegistrationFactory(project=self.public_project, is_public=True)
        self.registration_of_components = RegistrationFactory(project=self.private_project, is_public=True)
        registration_of_component = self.private_component.registrations_all[0]
        registration_of_component.is_public = True
        registration_of_component.save()

        self.embargoed_registration = RegistrationFactory(project=self.public_project, creator=self.user)
        self.embargoed_registration.embargo_registration(
            self.user,
            datetime.datetime.utcnow() + datetime.timedelta(days=10)
        )
        self.embargoed_registration.save()

        self.reg_to_be_withdrawn = RegistrationFactory(project=self.public_project)
        self.withdrawn_registration = WithdrawnRegistrationFactory(
            registration=self.reg_to_be_withdrawn,
            user=self.reg_to_be_withdrawn.creator
        )

        # Add Deleted Nodes
        self.deleted_node = ProjectFactory(is_deleted=True)
        self.deleted_node2 = ProjectFactory(is_deleted=True)

        self.date = datetime.datetime.utcnow() - datetime.timedelta(1)

        modify_node_dates_in_mongo(self.date - datetime.timedelta(0.1))

        self.results = NodeSummary().get_events(self.date.date())[0]

    def tearDown(self):
        super(TestNodeCount, self).tearDown()
        Node.remove()
        User.remove()

    def test_get_node_count(self):
        nodes = self.results['nodes']

        assert_equal(nodes['total'], 8)  # 3 Projects, 5 Registrations
        assert_equal(nodes['public'], 1)  # 1 Project
        assert_equal(nodes['private'], 2)  # 1 Project, 1 Component

    def test_get_project_count(self):
        projects = self.results['projects']

        assert_equal(projects['total'], 2)
        assert_equal(projects['public'], 1)
        assert_equal(projects['private'], 1)

    def test_get_registered_nodes_count(self):
        registered_nodes = self.results['registered_nodes']

        assert_equal(registered_nodes['total'], 5)
        assert_equal(registered_nodes['public'], 4)  # 3 Registrations, 1 Withdrawn registration
        assert_equal(registered_nodes['withdrawn'], 1)
        assert_equal(registered_nodes['embargoed'], 1)

    def test_get_registered_projects_count(self):
        registered_projects = self.results['registered_projects']

        assert_equal(registered_projects['total'], 4)  # Not including a Registration Component
        assert_equal(registered_projects['public'], 3)
        assert_equal(registered_projects['withdrawn'], 1)
        assert_equal(registered_projects['embargoed'], 1)
