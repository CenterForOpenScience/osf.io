from __future__ import unicode_literals
import sys
import logging

from website.app import init_app
from website.models import User
from scripts import utils as script_utils
from modularodm import Q
from bson.son import SON
from framework.mongo import database as db
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)

pipeline = [
    {"$unwind": "$emails"},
    {"$project": {"emails": {"$toLower": "$emails"}}},
    {"$group": {"_id": "$emails", "count": {"$sum": 1}}},
    {"$sort": SON([("count", -1), ("_id", -1)])}
]


def get_duplicate_email():
    duplicate_emails = []
    result = db['user'].aggregate(pipeline)
    for each in result['result']:
        if each['count'] > 1:
            duplicate_emails.append(each['_id'])
    return duplicate_emails


def log_duplicate_acount(dry):
    duplicate_emails = get_duplicate_email()
    count = 0
    if duplicate_emails:
        for email in duplicate_emails:
            users = User.find(Q('emails', 'eq', email) & Q('merged_by', 'eq', None) & Q('username', 'ne', None))
            for user in users:
                count += 1
                logger.info("User {}, username {}, id {}, email {} is a duplicate"
                            .format(user.fullname, user.username, user._id, user.emails))
    logger.info("Found {} users with duplicate emails".format(count))


def main():
    init_app(routes=False)  # Sets the storage backends on all models
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        log_duplicate_acount(dry)


if __name__ == '__main__':
    main()
