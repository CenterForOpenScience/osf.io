#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to remove unclaimed records for confirmed users. Once a user has
confirmed their email address, all their unclaimed records should be cleared
so that their full name shows up correctly on all projects.

To run: ::

    $ python -m scripts.clear_invalid_unclaimed_records

Log:

    - Run by SL on 2014-09-29. There were 35 migrated user records.
"""

import sys
import logging

from modularodm import Q
from nose.tools import *  # noqa (PEP8 asserts)

from website.app import init_app
from framework.auth.core import User
from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

QUERY = Q('date_confirmed', 'ne', None) & Q('unclaimed_records', 'ne', {})

def do_migration(dry=False):
    """Clear unclaimed_records for confirmed users."""
    n_migrated = 0
    for user in get_targets():
        n_migrated += 1
        logger.info('Clearing unclaimed records for {0!r}'.format(user))
        if not dry:
            user.unclaimed_records = {}
            user.save()
    logger.info('Migrated {0} records.'.format(n_migrated))
    return n_migrated

def get_targets():
    """Return a QuerySet containing confirmed Users who have unclaimed records."""
    return User.find(QUERY)

def main():
    init_app(routes=False)
    do_migration(dry='dry' in sys.argv)

class TestMigrateNodeCategories(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.referrer = UserFactory()
        self.project = ProjectFactory(creator=self.referrer)

    def test_get_targets(self):
        user = UserFactory.build()
        user.add_unclaimed_record(self.project, self.referrer, 'foo')
        user.save()
        assert_true(user.is_confirmed())

        targets = list(get_targets())
        assert_in(user, targets)

    def test_do_migration(self):
        user = UserFactory.build()
        user.add_unclaimed_record(self.project, self.referrer, 'foo')
        user.save()
        assert_true(user.is_confirmed())

        assert_equal(len(user.unclaimed_records.keys()), 1)
        do_migration()
        assert_equal(len(user.unclaimed_records.keys()), 0)

if __name__ == '__main__':
    main()
