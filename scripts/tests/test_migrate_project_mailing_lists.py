# -*- coding: utf-8 -*-
import mock
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

    @mock.patch('scripts.migrate_project_mailing_lists.create_list')
    def test_migrate_node(self, mock_create):
        node = ProjectFactory()
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_true(node.mailing_enabled)
        assert node._id in str(mock_create.call_args_list)

    @mock.patch('scripts.migrate_project_mailing_lists.create_list')
    def test_migrate_node_with_parent(self, mock_create):
        node = ProjectFactory(parent=NodeFactory())
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_true(node.mailing_enabled)
        assert node._id in str(mock_create.call_args_list)
        assert node.parent._id in str(mock_create.call_args_list)

    @mock.patch('scripts.migrate_project_mailing_lists.create_list')
    def test_migrate_registration(self, mock_create):
        node = RegistrationFactory()
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_false(node.mailing_enabled)
        assert node._id not in str(mock_create.call_args_list)

    @mock.patch('scripts.migrate_project_mailing_lists.create_list')
    def test_migrate_dashboard(self, mock_create):
        node = CollectionFactory()
        NotificationSubscription.remove()
        migrate(dry_run=False)
        assert_false(node.mailing_enabled)
        assert node._id not in str(mock_create.call_args_list)
