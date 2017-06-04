"""Ensure that confirmed users' usernames are included in their emails field.
"""

import logging
import sys

from modularodm import Q

from website import models
from website.app import init_app
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)


def main():
    # Set up storage backends
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    count = 0
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    logger.info("Finding users with username not in confirmed emails")
    for user in get_users_with_username_not_in_emails():
        user.emails.append(user.username)
        logger.info(repr(user))
        if not dry_run:
            user.save()
        count += 1
    logger.info('Migrated {} users'.format(count))


def get_users_with_username_not_in_emails():
    return (
        user for user in
        models.User.find(Q('date_confirmed', 'ne', None))
        if user.is_active and
        user.username.lower() not in [email.lower() for email in user.emails] and
        user.username is not None
    )

if __name__ == '__main__':
    main()
