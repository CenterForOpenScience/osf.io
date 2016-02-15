# -*- coding: utf-8 -*-
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import DashboardFactory
from tests.factories import NodeFactory
from tests.factories import ProjectFactory
from tests.factories import RegistrationFactory

from scripts.migrate_project_mailing_lists import migrate


class TestMigrateMailingLists(OsfTestCase):

    def test_migrate_node(self):
        node = ProjectFactory()
        migrate(dry_run=False)
        assert_true(node.mailing_enabled)

    def test_migrate_node_with_parent(self):
        node = ProjectFactory(parent=NodeFactory())
        migrate(dry_run=False)
        assert_true(node.mailing_enabled)
        

    def test_migrate_registration(self):
        node = RegistrationFactory()
        migrate(dry_run=False)
        assert_false(node.mailing_enabled)


    def test_migrate_dashboard(self):
        node = DashboardFactory()
        migrate(dry_run=False)
        assert_false(node.mailing_enabled)

