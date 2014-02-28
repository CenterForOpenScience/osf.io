#!/usr/bin/env
# -*- coding: utf-8 -*-

"""Migrates old-style unregistered users (dictionaries in Node#contributor_list)
to actual User records.
"""
import sys
import logging

from website import app, models
from tests.base import DbTestCase
from tests.factories import DeprecatedUnregUserFactory


logging.getLogger('factory.generate:BaseFactory').setLevel(logging.WARNING)


def main():
    app.init_app()


def migrate_user(user_dict):
    return user_dict

# To run tests: pytest scripts/migrate_unregistered.py
class TestMigratingUnreg(DbTestCase):

    def test_migrate_unreg(self):
        old_style = DeprecatedUnregUserFactory()
        user = migrate_user(old_style)
        assert isinstance(user, models.User)

if __name__ == '__main__':
    main()
