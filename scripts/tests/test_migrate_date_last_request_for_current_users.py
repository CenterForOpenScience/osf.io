from nose.tools import *

from datetime import datetime, timedelta
from tests.base import OsfTestCase
from tests import factories
from website import models

from scripts.migration.migrate_date_last_request_for_current_users import main


class TestMigrateDateLastRequest(OsfTestCase):
    def setUp(self):
        super(TestMigrateDateLastRequest, self).setUp()
        self.user = factories.UserFactory()
        self.user2 = factories.UserFactory()
        self.user3 = factories.UserFactory()

        self.users = [self.user, self.user2, self.user3]

        for user in self.users:
            user.__setattr__('date_last_login', datetime.utcnow())
            user.save()

        self.user3.date_last_request = (datetime.utcnow() + timedelta(hours=24))
        self.user3.save()


    def tearDown(self):
        super(TestMigrateDateLastRequest, self).tearDown()
        models.User.remove()

    def test_get_users(self):
        assert_equal(self.user.date_last_request, None)
        assert_equal(self.user2.date_last_request, None)
        assert_not_equal(self.user3.date_last_request, None)

        assert_not_equal(self.user.date_last_request, self.user.date_last_login)
        assert_not_equal(self.user2.date_last_request, self.user2.date_last_login)
        assert_not_equal(self.user3.date_last_request, self.user3.date_last_login)

        main(dry=False)

        for user in self.users:
            user.reload()

        assert_equal(self.user.date_last_request, self.user.date_last_login)
        assert_equal(self.user2.date_last_request, self.user2.date_last_login)
        assert_not_equal(self.user3.date_last_request, self.user3.date_last_login)
