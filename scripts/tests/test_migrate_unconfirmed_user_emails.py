from nose.tools import *

from scripts.migration.migrate_unconfirmed_user_emails import (
    get_users_with_unconfirmed_emails,
    remove_unconfirmed_emails,
)
from tests.base import OsfTestCase
from tests import factories
from website import models


class TestMigrateUnconfirmedEmails(OsfTestCase):
    def setUp(self):
        super(TestMigrateUnconfirmedEmails, self).setUp()
        self.registered_user = factories.UserFactory()
        self.unconfirmed = factories.UnconfirmedUserFactory()
        self.unregistered = factories.UnregUserFactory()
        self.unregistered.emails = [self.unregistered.username]
        self.unregistered.save()

    def tearDown(self):
        super(TestMigrateUnconfirmedEmails, self).tearDown()
        models.User.remove()

    def test_get_users(self):
        self.unregistered.reload()
        assert_equal(
            list(get_users_with_unconfirmed_emails()),
            [self.unregistered]
        )

    def test_fix_user(self):
        remove_unconfirmed_emails(self.unregistered)
        assert_equal(
            self.unregistered.emails,
            []
        )