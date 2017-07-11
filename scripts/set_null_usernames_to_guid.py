"""Find all User records that have username equal to None, and set their
username to their GUID in order to ensure uniqueness on the username field.
This was run as a prerequisite to the mongo -> postgres migration.
"""
import sys
import logging

from modularodm import Q

from website.app import init_app
from website.models import User
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def main(dry=True):
    count = 0
    for user in User.find(Q('username', 'eq', None)):
        logger.info('Setting username for {}'.format(user._id))
        if not dry:
            user.username = user._id
            user.save()
        count += 1
    logger.info('Migrated {} users.'.format(count))


if __name__ == "__main__":
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    main(dry=dry)
