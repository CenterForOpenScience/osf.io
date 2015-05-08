from nose.tools import *

from scripts.migration.migrate_confirmed_user_emails import (
    get_users_with_username_not_in_emails,
    add_username_to_emails,
)
from tests.base import OsfTestCase
from tests import factories
from website import models


class TestMigrateConfirmedEmails(OsfTestCase):
    def setUp(self):
        super(TestMigrateConfirmedEmails, self).setUp()
        self.incorrect = factories.UserFactory()
        self.incorrect.emails = []
        self.incorrect.save()

        self.correct = factories.UserFactory()

    def tearDown(self):
        super(TestMigrateConfirmedEmails, self).tearDown()
        models.User.remove()

    def test_get_users(self):
        assert_equal(
            [each._id for each in get_users_with_username_not_in_emails()],
            [self.incorrect._id]
        )

    def test_fix_user(self):
        assert_equal(
            self.incorrect.emails,
            []
        )
        add_username_to_emails(self.incorrect)
        assert_equal(
            self.incorrect.emails,
            [self.incorrect.username]
        )