"""
Used to transfer over subscriptions current users might have from their mailing_list field (which is to be deprecated),
to the new mailchimp_mailing_lists field. After that is done, to clean-up, remove mailing_lists as a User field.
"""
import logging
import sys

from website import models
from website.app import init_app
from modularodm import Q

logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    logger.warn('Users will have "mailchimp_mailing_lists" updated from deprecated field "mailing_lists" value')
    if dry_run:
        logger.warn('Dry_run mode')
    for user in get_users_needing_mailing_lists_update():
        logger.info('User {0} "mailchimp_mailing_lists" updated'.format(user.username))
        if not dry_run:
            user.mailchimp_mailing_lists = user.mailing_lists
            user.save()

def get_users_needing_mailing_lists_update():
    return models.User.find(
        Q('mailing_lists', 'ne', {})
    )

if __name__ == '__main__':
    main()
