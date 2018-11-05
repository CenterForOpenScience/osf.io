import datetime
from django.utils import timezone
from osf.models import AbstractNode
from tests.base import OsfTestCase
from osf_tests.factories import UserFactory, RegistrationFactory, ProjectFactory, WithdrawnRegistrationFactory
from nose.tools import *  # PEP8 asserts

from scripts.analytics.node_summary import NodeSummary


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

        self.embargoed_registration = RegistrationFactory(project=self.public_project, creator=self.public_project.creator)
        self.embargoed_registration.embargo_registration(
            self.embargoed_registration.creator,
            timezone.now() + datetime.timedelta(days=10)
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

        # Add Spam
        self.spam_node = ProjectFactory(spam_status=2)

        self.date = timezone.now() - datetime.timedelta(days=1)

        for node in AbstractNode.objects.all():
            node.created = self.date
            node.save()
        # modify_node_dates_in_mongo(self.date - datetime.timedelta(0.1))

        self.results = NodeSummary().get_events(self.date.date())[0]

    def test_counts(self):

    # test_get_node_count
        nodes = self.results['nodes']

        assert_equal(nodes['total'], 4)  # 2 Projects, 1 component, 1 spam node
        assert_equal(nodes['total_excluding_spam'], 3)  # 2 Projects, 1 component
        assert_equal(nodes['public'], 1)  # 1 Project
        assert_equal(nodes['private'], 3)  # 1 Project, 1 Component, 1 spam node (spam is always private)
        assert_equal(nodes['total_daily'], 4)  # 2 Projects, 1 component,  1 spam node
        assert_equal(nodes['total_daily_excluding_spam'], 3)  # 2 Projects, 1 component
        assert_equal(nodes['public_daily'], 1)  # 1 Project
        assert_equal(nodes['private_daily'], 3)  # 1 Project, 1 Component, 1 spam node

    # test_get_project_count
        projects = self.results['projects']

        assert_equal(projects['total'], 3)
        assert_equal(projects['total_excluding_spam'], 2)
        assert_equal(projects['public'], 1)
        assert_equal(projects['private'], 2)
        assert_equal(projects['total_daily'], 3)
        assert_equal(projects['total_daily_excluding_spam'], 2)
        assert_equal(projects['public_daily'], 1)
        assert_equal(projects['private_daily'], 2)


    # test_get_registered_nodes_count
        registered_nodes = self.results['registered_nodes']

        assert_equal(registered_nodes['total'], 5)
        assert_equal(registered_nodes['public'], 4)  # 3 Registrations, 1 Withdrawn registration
        assert_equal(registered_nodes['withdrawn'], 1)
        assert_equal(registered_nodes['embargoed'], 1)
        assert_equal(registered_nodes['embargoed_v2'], 1)
        assert_equal(registered_nodes['total_daily'], 5)
        assert_equal(registered_nodes['public_daily'], 4)  # 3 Registrations, 1 Withdrawn registration
        assert_equal(registered_nodes['withdrawn_daily'], 1)
        assert_equal(registered_nodes['embargoed_daily'], 1)
        assert_equal(registered_nodes['embargoed_v2_daily'], 1)

    # test_get_registered_projects_count
        registered_projects = self.results['registered_projects']

        assert_equal(registered_projects['total'], 4)  # Not including a Registration Component
        assert_equal(registered_projects['public'], 3)
        assert_equal(registered_projects['withdrawn'], 1)
        assert_equal(registered_projects['embargoed'], 1)
        assert_equal(registered_projects['embargoed_v2'], 1)

        assert_equal(registered_projects['total_daily'], 4)
        assert_equal(registered_projects['public_daily'], 3)
        assert_equal(registered_projects['withdrawn_daily'], 1)
        assert_equal(registered_projects['embargoed_daily'], 1)
        assert_equal(registered_projects['embargoed_v2_daily'], 1)

        # Modify date to zero out dailies
        for node in AbstractNode.objects.all():
            node.created = self.date - datetime.timedelta(days=1)
            node.save()

        self.results = NodeSummary().get_events(self.date.date())[0]

    # test_get_node_count daily zero
        nodes = self.results['nodes']

        assert_equal(nodes['total'], 4)  # 2 Projects, 1 component, 1 spam node
        assert_equal(nodes['public'], 1)  # 1 Project
        assert_equal(nodes['private'], 3)  # 1 Project, 1 Component, 1 spam node

        assert_equal(nodes['total_daily'], 0)  # 2 Projects, 1 component
        assert_equal(nodes['total_daily_excluding_spam'], 0)
        assert_equal(nodes['public_daily'], 0)  # 1 Project
        assert_equal(nodes['private_daily'], 0)  # 1 Project, 1 Component

    # test_get_project_count daily zero
        projects = self.results['projects']

        assert_equal(projects['total'], 3)
        assert_equal(projects['public'], 1)
        assert_equal(projects['private'], 2)

        assert_equal(projects['total_daily'], 0)
        assert_equal(projects['total_daily_excluding_spam'], 0)
        assert_equal(projects['public_daily'], 0)
        assert_equal(projects['private_daily'], 0)

    # test_get_registered_nodes_count daily zero
        registered_nodes = self.results['registered_nodes']

        assert_equal(registered_nodes['total'], 5)
        assert_equal(registered_nodes['public'], 4)  # 3 Registrations, 1 Withdrawn registration
        assert_equal(registered_nodes['withdrawn'], 1)
        assert_equal(registered_nodes['embargoed'], 1)
        assert_equal(registered_nodes['embargoed_v2'], 1)

        assert_equal(registered_nodes['total_daily'], 0)
        assert_equal(registered_nodes['public_daily'], 0)  # 3 Registrations, 1 Withdrawn registration
        assert_equal(registered_nodes['withdrawn_daily'], 0)
        assert_equal(registered_nodes['embargoed_daily'], 0)
        assert_equal(registered_nodes['embargoed_v2_daily'], 0)

    # test_get_registered_projects_count daily zero
        registered_projects = self.results['registered_projects']

        assert_equal(registered_projects['total'], 4)  # Not including a Registration Component
        assert_equal(registered_projects['public'], 3)
        assert_equal(registered_projects['withdrawn'], 1)
        assert_equal(registered_projects['embargoed'], 1)
        assert_equal(registered_projects['embargoed_v2'], 1)

        assert_equal(registered_projects['total_daily'], 0)
        assert_equal(registered_projects['public_daily'], 0)
        assert_equal(registered_projects['withdrawn_daily'], 0)
        assert_equal(registered_projects['embargoed_daily'], 0)
        assert_equal(registered_projects['embargoed_v2_daily'], 0)
