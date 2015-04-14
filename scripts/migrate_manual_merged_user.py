import sys
import logging

from website.app import init_app
from website.models import User
from scripts import utils as script_utils
from modularodm import Q

logger = logging.getLogger(__name__)


def do_migration(records):
    for user in records:
        log_info(user)
        user.username = None
        user.password = None
        user.email_verifications = {}
        user.verification_key = None
        user.save()
    logger.info('Migrated {0} users'.format(len(records)))


def get_targets():
    return User.find(Q('merged_by', 'ne', None) & Q('username', 'ne', None))


def log_info(user):
    logger.info(
        'Migrating user - {}: merged_by={}, '
        'username={}, password={}, '
        'email_verification={}, verification_key={}'.format(
            user._id,
            user.merged_by,
            user.username,
            user.password,
            user.email_verifications,
            user.verification_key
        )
    )


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    if 'dry' in sys.argv:
        user_list = get_targets()
        for user in user_list:
            log_info(user)
        logger.info('[dry] Migrated {0} users'.format(len(user_list)))
    else:
        do_migration(get_targets())


if __name__ == '__main__':
    if 'dry' not in sys.argv:
        script_utils.add_file_logger(logger, __file__)
    main()
