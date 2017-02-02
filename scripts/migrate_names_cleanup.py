#!/usr/bin/env python
# encoding: utf-8
"""Migrate user name fields

Run dry run: python -m scripts.migrate_names_cleanup dry
Run migration: python -m scripts.migrate_names_cleanup

Log: Run by sloria on 2015-02-17. A log was saved to /opt/data/migration-logs.
"""
import sys
import logging

from modularodm import Q

from website.app import init_app
from framework.auth import core

from scripts import utils as script_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def migrate_user(user, dry_run):
    if user.fullname and user.fullname != user.fullname.strip():
        logger.info(u'Updated User: {}, fullname: "{}"'.format(user._id, user.fullname))
        user.fullname = user.fullname.strip()

    if user.given_name and user.given_name != user.given_name.strip():
        logger.info(u'Updated User: {}, given_name: "{}"'.format(user._id, user.given_name))
        user.given_name = user.given_name.strip()

    if user.middle_names and user.middle_names != user.middle_names.strip():
        logger.info(u'Updated User: {}, middle_names: "{}"'.format(user._id, user.middle_names))
        user.middle_names = user.middle_names.strip()

    if user.family_name and user.family_name != user.family_name.strip():
        logger.info(u'Updated User: {}, family_name: "{}"'.format(user._id, user.family_name))
        user.family_name = user.family_name.strip()

    if user.suffix and user.suffix != user.suffix.strip():
        logger.info(u'Updated User: {}, suffix: "{}"'.format(user._id, user.suffix))
        user.suffix = user.suffix.strip()

    if not dry_run:
        user.save()


def get_targets():
    return core.User.find()


def main(dry_run):
    users = get_targets()
    for user in users:
        migrate_user(user, dry_run)


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    dry_run = 'dry' in sys.argv

    # Log to file
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)

    main(dry_run=dry_run)


import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from addons.osfstorage.tests.factories import AuthUserFactory


class TestMigrateUser(OsfTestCase):

    def tearDown(self):
        super(TestMigrateUser, self).tearDown()
        core.User.remove()

    def test_get_targets(self):
        [AuthUserFactory() for _ in range(5)]
        targets = get_targets()
        assert_equal(len(targets), 5)

    def test_migrate_user(self):
        user = AuthUserFactory()
        orig_user = user
        user.fullname = '   {}    '.format(user.fullname)
        user.given_name = '   {}    '.format(user.given_name)
        user.middle_names = '   {}    '.format(user.middle_names)
        user.family_name = '   {}    '.format(user.family_name)
        user.suffix = '   {}    '.format(user.suffix)
        user.save()

        migrate_user(user, dry_run=False)
        user.reload()

        assert_equal(user.fullname, orig_user.fullname)
        assert_equal(user.given_name, orig_user.given_name)
        assert_equal(user.middle_names, orig_user.middle_names)
        assert_equal(user.family_name, orig_user.family_name)
        assert_equal(user.suffix, orig_user.suffix)

    @mock.patch('scripts.migrate_names_cleanup.get_targets')
    def test_dry_run(self, mock_targets):
        user1 = mock.Mock()
        user1.fullname = '    {}    '.format('tea g. pot')
        user2 = mock.Mock()
        user2.fullname = 'normal name'
        users = [user1, user2]
        mock_targets.return_value = users
        main(dry_run=True)

        for user in users:
            assert not user.save.called
