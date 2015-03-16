# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import UserFactory
from tests.factories import NodeFactory
from tests.test_conferences import ConferenceFactory

from scripts.migrate_conference_admins import migrate_node


class TestMigrateAdmins(OsfTestCase):

    def test_migrate_node(self):
        external_admin = UserFactory()
        personal_admin = UserFactory()
        staff_user = UserFactory()
        personal_accounts = [personal_admin.username]
        conference = ConferenceFactory(admins=[external_admin, personal_admin])
        node = NodeFactory()
        node.add_contributor(staff_user)
        node.add_contributor(external_admin)
        node.add_contributor(personal_admin)
        migrate_node(node, conference, staff_user, personal_accounts, dry_run=False)
        node.reload()
        assert_in(staff_user, node.contributors)
        assert_in(external_admin, node.contributors)
        assert_not_in(personal_admin, node.contributors)
        # Verify that migration is idempotent
        migrate_node(node, conference, staff_user, personal_accounts, dry_run=False)
        node.reload()
        assert_in(staff_user, node.contributors)
        assert_in(external_admin, node.contributors)
        assert_not_in(personal_admin, node.contributors)
