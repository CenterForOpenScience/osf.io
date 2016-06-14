# -*- coding: utf-8 -*-
"""Migrate users whose email_verifications=None to have
email_verifications={} (which is now the default value).
"""
import sys
import logging

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.models import User
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def do_migration():
    users = User.find(Q('email_verifications', 'eq', None))
    migrated = 0
    for user in users:
        logger.info('Setting email_verifications for user {} to {{}}'.format(user._id))
        user.email_verifications = {}
        user.save()
        migrated += 1
    logger.info('Migrated {} users'.format(migrated))


def main(dry=True):
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        do_migration()
        if dry:
            raise Exception('Abort Transaction - Dry Run')

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
