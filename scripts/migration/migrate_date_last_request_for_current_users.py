"""
Used to add users date_last_request, value set equal to date_last_login.
"""

import sys
import logging
from modularodm import Q
from website.app import init_app
from website import models
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)


def main(dry=True):
    init_app(routes=False)
    users = models.User.find(Q('date_last_request', 'eq', None))
    logger.warn('All active users will have a date_last_request field added and set equal to date_last_login.')

    for user in users:
        if user.is_active:
            user.date_last_request = user.date_last_login
            user.save()
            logger.info('User {0} "date_last_request" added'.format(user._id))
    if dry:
        raise RuntimeError('Dry run -- transaction rolled back')

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        main(dry=True)

