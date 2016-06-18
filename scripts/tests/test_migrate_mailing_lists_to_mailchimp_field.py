from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import UserFactory
from scripts.migration.migrate_mailing_lists_to_mailchimp_field import main, get_users_with_no_mailchimp_mailing_lists

class TestMigrateMailingLists(OsfTestCase):

    def setUp(self):
        super(TestMigrateMailingLists, self).setUp()
        self.user1 = UserFactory(mailing_lists={'mail': True})
        self.user2 = UserFactory(mailing_lists={'mail': False})
        self.user3 = UserFactory()
        self.user1.save()
        self.user2.save()

    def test_get_users_with_mailing_lists(self):
        users_with_mailing_list_ids = [user._id for user in get_users_with_no_mailchimp_mailing_lists()]

        assert_equal(len(users_with_mailing_list_ids), 2)

        assert_true(self.user1._id in users_with_mailing_list_ids)
        assert_true(self.user2._id in users_with_mailing_list_ids)
        assert_false(self.user3._id in users_with_mailing_list_ids)

    def test_migration_of_mailing_lists(self):

        assert_equal(self.user1.mailchimp_mailing_lists, {})
        assert_equal(self.user2.mailchimp_mailing_lists, {})

        main()

        self.user1.reload()
        self.user2.reload()
        assert_true(self.user1.mailchimp_mailing_lists.get(u'mail'))
        assert_false(self.user2.mailchimp_mailing_lists.get(u'mail'))
