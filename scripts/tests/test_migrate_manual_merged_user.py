from tests.base import OsfTestCase
from tests.factories import UserFactory
from scripts.migrate_manual_merged_user import (
    do_migration,
    get_targets,
)

class TestMigrateManualMergedUser(OsfTestCase):

    def test_get_targets(self):
        user1 = UserFactory.build(merged_by=None)
        user2 = UserFactory.build(merged_by=user1)
        user3 = UserFactory.build()
        user1.save()
        user2.save()
        user3.save()

        user_list = get_targets()
        assert user_list is not None
        assert len(user_list) is 1

        user1.merged_by = user3
        user1.save()
        user_list = get_targets()
        assert len(user_list) is 2

    def test_do_migration(self):
        user1 = UserFactory.build(merged_by=None)
        user2 = UserFactory.build(merged_by=user1, verification_key="key1")
        user3 = UserFactory.build(merged_by=user1, verification_key="key2")
        user2.email_verifications['token'] = {'email': 'test@example.com'}
        user3.email_verifications['token'] = {'email': 'test@example.com'}
        user1.save()
        user2.save()
        user3.save()

        user_list = get_targets()
        do_migration(user_list)

        user2.reload()
        user3.reload()

        assert user2.username is None
        assert user2.password is None
        assert len(user2.email_verifications) is 0
        assert user2.verification_key is None
        assert user3.username is None
        assert user3.password is None
        assert len(user3.email_verifications) is 0
        assert user3.verification_key is None
