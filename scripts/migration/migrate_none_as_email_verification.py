""" Ensure that users with User.email_verifications == None now have {} instead
"""

import logging
import sys
from modularodm import Q
from nose.tools import *
from website import models
from website.app import init_app
from scripts import utils as scripts_utils

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def main():
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    count = 0

    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    logger.info("Iterating users with None as their email_verification")
    for user in get_users_with_none_in_email_verifications():
        user.email_verifications = {}
        count += 1
        logger.info(repr(user))
        if not dry_run:
            user.save()

    logger.info('Done with {} users migrated'.format(count))

def get_users_with_none_in_email_verifications():
    return models.User.find(Q('email_verifications', 'eq', None))

if __name__ == '__main__':
    main()
