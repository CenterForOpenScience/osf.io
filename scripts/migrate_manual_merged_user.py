import sys
import logging

from website.app import init_app
from website.models import User
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)


def do_migration(records, dry=False):
    for user in records:
        log_info(user)
        if not dry:
            user.username = None
            user.password = None
            user.email_verifications = {}
            user.verification_key = None
            user.save()
    logger.info('{}Migrated {} users'.format('[dry]'if dry else '', len(records)))


def get_targets():
    return User.find(Q('merged_by', 'ne', None) & Q('username', 'ne', None))


def log_info(user):
    logger.info(
        'Migrating user - {}: merged_by={}, '.format(
            user._id,
            user.merged_by._id,
        )
    )


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    do_migration(get_targets(), dry)


if __name__ == '__main__':
    main()
