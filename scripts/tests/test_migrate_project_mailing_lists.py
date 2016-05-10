# -*- coding: utf-8 -*-
from nose.tools import *  # noqa

from website.models import Node, NotificationSubscription
from tests.base import OsfTestCase
from tests.factories import CollectionFactory
from tests.factories import NodeFactory
from tests.factories import ProjectFactory
from tests.factories import RegistrationFactory

from scripts.migrate_project_mailing_lists import migrate


class TestMigrateMailingLists(OsfTestCase):

    def tearDown(self):
        # Prevent errors
        Node.remove()
        NotificationSubscription.remove()

    def test_migrate_node(self):
        node = ProjectFactory()
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_true(node.mailing_enabled)

    def test_migrate_node_with_parent(self):
        node = ProjectFactory(parent=NodeFactory())
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_true(node.mailing_enabled)
        

    def test_migrate_registration(self):
        node = RegistrationFactory()
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_false(node.mailing_enabled)


    def test_migrate_dashboard(self):
        node = CollectionFactory()
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_false(node.mailing_enabled)

