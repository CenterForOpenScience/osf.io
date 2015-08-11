# -*- coding: utf-8 -*-

import mock

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory
from tests.factories import ProjectFactory
from tests.factories import NodeFactory

from scripts.migrate_project_mailing_lists import migrate_node


class TestMigrateMailingLists(OsfTestCase):

    @mock.patch('scripts.migrate_project_mailing_lists.create_list')
    def test_migrate_top_level_node(self, mock_create_list):
        node = ProjectFactory(parent=None)
        migrate_node(node)
        mock_create_list.assert_called()

    @mock.patch('scripts.migrate_project_mailing_lists.create_list')
    def test_migrate_node_with_parent(self, mock_create_list):
        node = NodeFactory()
        migrate_node(node)
        mock_create_list.assert_not_called()

    def test_registered_and_unregistered_users(self):
        creator = UserFactory()
        node = NodeFactory(creator=creator)
