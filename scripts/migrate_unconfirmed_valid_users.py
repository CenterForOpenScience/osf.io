#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate users with a valid date_last_login but no date_confirmed."""

import sys
import logging

from website.app import init_app
from website.models import User
from scripts import utils as script_utils
from tests.base import OsfTestCase
from tests.factories import UserFactory
from modularodm import Q
import datetime as dt

logger = logging.getLogger(__name__)

def do_migration(records):
    for user in records:
        log_info(user)
        user.date_confirmed = user.date_last_login
        if not user.is_registered:
            user.is_registered = True
        user.save()
    logger.info('Migrated {0} users'.format(len(records)))


def get_targets():
    return User.find(Q('date_confirmed', 'eq', None) & Q('date_last_login', 'ne', None))


def log_info(user):
    logger.info(
        'Migrating user - {}: date_confirmed={}, '
        'date_last_login={}, is_registered={}'.format(
            user._id,
            user.date_confirmed,
            user.date_last_login,
            user.is_registered
        )
    )


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    if 'dry' in sys.argv:
        user_list = get_targets()
        for user in user_list:
            log_info(user)
        logger.info('[dry] Migrated {0} users'.format(len(user_list)))
    else:
        do_migration(get_targets())

class TestMigrateNodeCategories(OsfTestCase):

    def test_get_targets(self):
        today = dt.datetime.utcnow()
        user1 = UserFactory.build(date_confirmed=today, date_last_login=today)
        user2 = UserFactory.build(date_confirmed=None, date_last_login=today)
        user1.save()
        user2.save()

        user_list = get_targets()
        assert user_list is not None
        assert len(user_list) is 1

        user1.date_confirmed = None
        user1.save()
        user_list = get_targets()
        assert len(user_list) is 2

    def test_do_migration(self):
        today = dt.datetime.utcnow()
        user1 = UserFactory.build(date_confirmed=None, date_last_login=today, is_registered=False)
        user2 = UserFactory.build(date_confirmed=None, date_last_login=today, is_registered=True)
        user1.save()
        user2.save()

        user_list = User.find(Q('_id', 'eq', user1._id) | Q('_id', 'eq', user2._id))
        do_migration(user_list)

        assert user1.date_confirmed is today
        assert user1.is_registered
        assert user2.date_confirmed is today
        assert user2.is_registered


if __name__ == '__main__':
    if 'dry' not in sys.argv:
        script_utils.add_file_logger(logger, __file__)
    main()
