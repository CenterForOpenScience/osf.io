"""Removes User.username from User.emails for unconfirmed users.

"""

import logging
import sys

from modularodm import Q
from nose.tools import *

from website import models
from website.app import init_app
from scripts import utils as scripts_utils
from tests import factories
from tests.base import OsfTestCase


logger = logging.getLogger(__name__)


def main():
    # Set up storage backends
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    logger.info("Iterating users with unconfirmed email"
                "s")
    for user in get_users_with_unconfirmed_emails():
        remove_unconfirmed_emails(user)
        logger.info(repr(user))
        if not dry_run:
            user.save()


def get_users_with_unconfirmed_emails():
    return models.User.find(
        Q('date_confirmed', 'eq', None)
        & Q('emails', 'ne', [])
    )


def remove_unconfirmed_emails(user):
    user.emails = []


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


if __name__ == '__main__':
    main()
