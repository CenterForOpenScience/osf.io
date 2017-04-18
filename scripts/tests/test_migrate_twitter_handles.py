from nose.tools import *

from scripts.migration.migrate_twitter_handles import (
    get_targets,
    migrate
)

from tests.base import OsfTestCase
from tests.factories import UserFactory

class TestMigrateTwitterHandles(OsfTestCase):
    def setUp(self):
        super(TestMigrateTwitterHandles, self).setUp()
        # User 2 has no '@' signs, should be unaffected by migration
        self.user1 = UserFactory()
        self.user1.social['twitter'] = 'user1'
        self.user1.save()
        # User 2 has 1 leading '@', should be changed to 'user2' after migration
        self.user2 = UserFactory()
        self.user2.social['twitter'] = '@user2'
        self.user2.save()
        # User 3 has 2 leading '@', should be changed to 'user1' after migration
        self.user3 = UserFactory()
        self.user3.social['twitter'] = '@@user3'
        self.user3.save()
        # User 4 has many leading '@' signs, should be changed to 'user4' after migration
        self.user4 = UserFactory()
        self.user4.social['twitter'] = '@@@@@@@@@@@@@@@@@user4'
        self.user4.save()
        # User 5 has '@' signs in the middle of their handle, should be changed to 'user5' after migration
        self.user5 = UserFactory()
        self.user5.social['twitter'] = 'user@@@@@@@5'
        self.user5.save()
        # User 6 has '@' signs at the end of their handle, should be changed to 'user5' after migration
        self.user6 = UserFactory()
        self.user6.social['twitter'] = 'user6@@@@@@'
        self.user6.save()
        # User 7 has no twitter handle, should be unaffected by migration
        self.user7 = UserFactory()
        self.user7.social['twitter'] = ''
        self.user7.save()

    def test_get_targets(self):
        # Initial targets should include: user2, user3, user4, user5, user6 (5 in total)
        users = get_targets()
        assert_equal(len(users), 5)

    def test_migrate(self):
        users = get_targets()
        migrate(users, dry_run=False)
        updated_users = get_targets()
        # Make sure all handles containing '@' have been migrated
        assert_equal(len(updated_users), 0)
        # Make sure each user's twitter handle is as expected
        assert_equal(self.user1.social['twitter'], 'user1')
        # Reload all users
        self.user1.reload()
        self.user2.reload()
        self.user3.reload()
        self.user4.reload()
        self.user5.reload()
        self.user6.reload()
        assert_equal(self.user1.social['twitter'], 'user1')
        assert_equal(self.user2.social['twitter'], 'user2')
        assert_equal(self.user3.social['twitter'], 'user3')
        assert_equal(self.user4.social['twitter'], 'user4')
        assert_equal(self.user5.social['twitter'], 'user5')
        assert_equal(self.user6.social['twitter'], 'user6')
        assert_equal(self.user7.social['twitter'], '')