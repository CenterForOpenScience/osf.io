from tests.base import OsfTestCase
from tests.factories import UserFactory
from nose.tools import *

from scripts.migration.migrate_none_as_email_verification import main as do_migration

class TestMigrateDates(OsfTestCase):
    def setUp(self):
        super(TestMigrateDates, self).setUp()
        self.user1 = UserFactory(email_verfications=None)
        self.user2 = UserFactory(email_verfications={})

    def test_migrate_none_as_email(self):
        do_migration()
        assert_equal(self.user1.email_verifications, {})
        assert_not_equal(self.user2.email_verifications, None)

