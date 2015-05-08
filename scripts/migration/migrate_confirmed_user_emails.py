"""Ensure that users with User.emails == [] have User.username inserted.

"""

import logging
import sys

from modularodm import Q
from nose.tools import *

from website import models
from website.app import init_app
from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)


def main():
    # Set up storage backends
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    logger.info("Iterating users with username not in confirmed emails")
    for user in get_users_with_username_not_in_emails():
        add_username_to_emails(user)
        logger.info(repr(user))
        if not dry_run:
            user.save()


def get_users_with_username_not_in_emails():
    return models.User.find(
        Q('date_confirmed', 'ne', None)
        & Q('emails', 'eq', [])
    )


def add_username_to_emails(user):
    user.emails.append(user.username)


if __name__ == '__main__':
    main()
