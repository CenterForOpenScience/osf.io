"""Merge User records that have the same username. Run in order to make user collection
conform with the unique constraint on User.username.
"""
import sys
import logging

from modularodm import Q

from website.app import init_app
from website.models import User
from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def find_primary_and_secondaries(users):
    """Given a list of users with the same username, find the user who should be the primary
    user into which the other users will be merged. Return a tuple (primary_user, list_of_secondary_users)
    """
    actives = [each for each in users if each.is_active]
    # If there is only one active User, that user is the primary
    if len(actives) == 1:
        primary = actives[0]
    # No active users, user who has earliest date_registered is primary
    elif len(actives) == 0:
        primary = sorted(users, key=lambda user: user.date_registered)[0]
    # Multiple active users, take the user with latest date_last_login
    else:
        users_with_dll = [each for each in actives if each.date_last_login]
        if len(users_with_dll) == 0:
            raise AssertionError(
                'Multiple active users with no date_last_login. '
                'Perform the merge manually.'
            )
        else:
            primary = sorted(users_with_dll, key=lambda user: user.date_last_login, reverse=True)[0]
    secondaries = list(users)
    secondaries.remove(primary)
    return primary, secondaries


def main(dry=True):
    duplicates = database.user.aggregate([
        {
            "$group": {
                "_id": "$username",
                "ids": {"$addToSet": "$_id"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {
                "count": {"$gt": 1},
                "_id": {"$ne": None}
            }
        },
        {
            "$sort": {
                "count": -1
            }
        }
    ]).get('result')
    # [
    #   {
    #       'count': 5,
    #       '_id': 'duplicated@username.com',
    #       'ids': [
    #           'listo','fidst','hatma','tchth','euser','name!'
    #       ]
    #   }
    # ]
    logger.info('Found {} duplicate usernames.'.format(len(duplicates)))
    for duplicate in duplicates:
        logger.info(
            'Found {} copies of {}: {}'.format(
                len(duplicate.get('ids')),
                duplicate.get('_id'),
                ', '.join(duplicate['ids'])
            )
        )
        users = list(User.find(Q('_id', 'in', duplicate.get('ids'))))
        primary, secondaries = find_primary_and_secondaries(users)
        for secondary in secondaries:
            logger.info('Merging user {} into user {}'.format(secondary._id, primary._id))
            # don't just rely on the toku txn and prevent a call to merge_user 
            # when doing a dry run because merge_user does more than just
            # db updateds (mailchimp calls, elasticsearch, etc.)
            if not dry:
                with TokuTransaction():
                    primary.merge_user(secondary)
                    primary.save()
                    secondary.save()
    logger.info('Finished migrating {} usernames'.format(len(duplicates)))

if __name__ == "__main__":
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    main(dry=dry)
