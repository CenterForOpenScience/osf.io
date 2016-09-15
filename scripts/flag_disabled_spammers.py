import logging
import sys

from modularodm import Q

from framework.auth.core import User
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app

logger = logging.getLogger(__name__)

def get_possible_spam_users():
    users = User.find(
        Q('system_tags', 'nin', ['spam_confirmed', 'ham_confirmed', 'spam_flagged']) &
        Q('date_disabled', 'ne', None) &
        Q('is_registered', 'eq', False)
    )
    logger.info('Found {} possible spam users'.format(users.count()))
    return users

def migrate():
    spam_count = 0
    spammy = get_possible_spam_users()
    for user in spammy:
        if any((n.is_spam for n in user.contributor_to)):
            logger.info('Confirmed user {}: "{}" as SPAM'.format(user._id, user.fullname))
            user.system_tags.append('spam_confirmed')
            user.save()
            spam_count += 1
        else:
            logger.info('User {}: "{}" smells like HAM'.format(user._id, user.fullname))
    logger.info('Flagged {} users as SPAM'.format(spam_count))

def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate()
        if dry_run:
            raise Exception('Dry Run -- Aborting Transaction')

if __name__ == '__main__':
    main()
