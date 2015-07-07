#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate nodes with invalid categories."""

import sys
import logging

from modularodm import Q

from website.app import init_app
from website.models import User
from scripts import utils as script_utils

logger = logging.getLogger('fix_is_claimed')


def main(dry=True):
    init_app(set_backends=True, routes=False)
    count = 0
    for user in User.find(Q('is_claimed', 'eq', None)):
        is_claimed = bool(user.date_confirmed)
        logger.info('User {}: setting is_claimed to {}'.format(user._id, is_claimed))
        user.is_claimed = is_claimed
        count += 1
        if not dry:
            user.save()
    logger.info('Migrated {} users.'.format(count))

if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
