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
        user.date_confirmed = user.date_last_login
        if not user.is_registered:
            user.is_registered = True
        logger.info('Finished migrating user {0}'.format(user._id))

def get_targets():
    return User.find(Q('date_confirmed', 'eq', None) & Q('date_last_login', 'ne', None))

def main():
    init_app(routes=False)  # Sets the storage backends on all models
    if 'dry' in sys.argv:
        for user in get_targets():
            print(user)
    else:
        do_migration(get_targets())

class TestMigrateNodeCategories(OsfTestCase):

    def test_get_targets(self):
        test = User.find(Q('date_confirmed', 'ne', None) & Q('date_last_login', 'ne', None))
        assert test is not None

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
    script_utils.add_file_logger(logger, __file__)
    main()
