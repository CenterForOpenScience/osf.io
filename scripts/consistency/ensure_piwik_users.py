#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Ensure all users have a corresponding Piwik user
"""

import logging
import sys

from modularodm import Q

from framework.analytics import piwik
from framework.auth.core import User
from scripts import utils as scripts_utils
from website.app import init_app


logger = logging.getLogger(__name__)


def get_users():
    return User.find(Q('piwik_token', 'eq', None))


def main():
    init_app('website.settings', set_backends=True, routes=False)

    if 'dry' in sys.argv:
        if 'list' in sys.argv:
            logger.info('=== Users not provisioned in Piwik ===')
            for user in get_users():
                logger.info(user._id)
        else:
            logger.info('{} Users to be updated'.format(get_users().count()))
    else:
        # Log to a file
        scripts_utils.add_file_logger(logger, __file__)
        users = get_users()
        logger.info('=== Updating {} Users ==='.format(users.count()))
        for user in users:
            piwik._create_user(user)
            logger.info(user._id)


if __name__ == "__main__":
    main()
