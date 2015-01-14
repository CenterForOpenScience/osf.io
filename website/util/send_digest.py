"""Script for sending OSF email digests to subscribed users and removing the records once sent."""

import datetime
from bson.code import Code
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from framework.auth.core import User
from framework.mongo import database as db
from website import mails
from website.app import init_app


def main():
    init_app(routes=False)
    grouped_digests = group_digest_notifications_by_user()
    send_digest(grouped_digests)


def send_digest(grouped_digests):
    for group in grouped_digests:
        try:
            user = User.find_one(Q('_id', 'eq', group['user_id']))
        except NoResultsFound:
            # ignore for now, but raise error here
            user = None

        messages = group['messageContexts']
        if user and messages:
            mails.send_mail(
                to_addr=user.username,
                mail=mails.DIGEST,
                name=user.fullname,
                content=messages)

    db.digestnotification.remove({'timestamp': {'$lt': datetime.datetime.utcnow(),
                                                '$gte': datetime.datetime.utcnow()-datetime.timedelta(hours=24)}})


def group_digest_notifications_by_user():
    return db['digestnotification'].group(
        key={'user_id': 1},
        condition={'timestamp': {'$lt': datetime.datetime.utcnow(),
                                 '$gte': datetime.datetime.utcnow()-datetime.timedelta(hours=24)}},
        initial={'messageContexts': []},
        reduce=Code("""function(curr, result) {
                            result.messageContexts.push(curr.context);
                    };
                    """))


if __name__ == '__main__':
    main()
