# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory
from tests.factories import NodeFactory
from tests.test_conferences import ConferenceFactory

from scripts.migrate_conference_admins import migrate_node


class TestMigrateAdmins(OsfTestCase):

    def test_migrate_node(self):
        conference = ConferenceFactory()
        node = NodeFactory(creator=conference.admins[0])
        staff_user = UserFactory()
        migrate_node(node, conference, staff_user, dry_run=False)
        node.reload()
        assert_in(staff_user, node.contributors)
        assert_not_in(conference.admins[0], node.contributors)
        # Verify that migration is idempotent
        migrate_node(node, conference, staff_user, dry_run=False)
        node.reload()
        assert_in(staff_user, node.contributors)
        assert_not_in(conference.admins[0], node.contributors)
