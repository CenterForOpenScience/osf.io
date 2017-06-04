from nose.tools import *

from scripts.dataverse.migrate_demo_host import (
    migrate, get_targets, OLD_HOST, NEW_HOST
)
from tests.base import OsfTestCase
from website.addons.dataverse.tests.factories import DataverseAccountFactory

class TestDemoHostMigration(OsfTestCase):

    def setUp(self):
        super(TestDemoHostMigration, self).setUp()
        self.account = DataverseAccountFactory(display_name=OLD_HOST, oauth_key=OLD_HOST)

    def test_migration(self):
        assert_equal(self.account.display_name, OLD_HOST)
        assert_equal(self.account.oauth_key, OLD_HOST)

        migrate(dry_run=False)
        self.account.reload()

        assert_equal(self.account.display_name, NEW_HOST)
        assert_equal(self.account.oauth_key, NEW_HOST)

    def test_get_targets(self):
        accounts = [DataverseAccountFactory() for n in range(10)]
        targets = get_targets()
        [assert_equal(x.provider, self.account.provider) for x in self.account.__class__.find()]
        assert_equal(self.account.__class__.find().count(), 11)
        assert_equal(targets.count(), 1)
        assert_equal(targets[0]._id, self.account._id)
