"""Script for sending OSF email digests to subscribed users and removing the records once sent."""

import datetime
import urlparse
from bson.code import Code
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from framework.auth.core import User
from framework.mongo import database as db
from website import mails, settings
from website.app import init_app
from website.util import web_url_for
from website.notifications.utils import NotificationsDict


def main():
    init_app(routes=False)
    grouped_digests = group_digest_notifications_by_user()
    print send_digest(grouped_digests)


def send_digest(grouped_digests):
    for group in grouped_digests:
        try:
            user = User.find_one(Q('_id', 'eq', group['user_id']))
        except NoResultsFound:
            # ignore for now, but raise error here
            user = None

        info = group['info']
        sorted_messages = group_messages(info)

        if user and sorted_messages:
            mails.send_mail(
                to_addr=user.username,
                mail=mails.DIGEST,
                name=user.fullname,
                message=sorted_messages,
                url=urlparse.urljoin(settings.DOMAIN, web_url_for('user_notifications'))
            )

    db.digestnotification.remove({'timestamp': {'$lt': datetime.datetime.utcnow(),
                                                '$gte': datetime.datetime.utcnow()-datetime.timedelta(hours=24)}})


def group_messages(notifications):
    d = NotificationsDict()
    for n in notifications:
        d.add_message(n['node_lineage'], n['message'])
    return d


def group_digest_notifications_by_user():
    return db['digestnotification'].group(
        key={'user_id': 1},
        condition={'timestamp': {'$lt': datetime.datetime.utcnow(),
                                 '$gte': datetime.datetime.utcnow()-datetime.timedelta(hours=24)}},
        initial={'info': []},
        reduce=Code("""function(curr, result) {
                            info = {
                                'message': {
                                    'message': curr.message,
                                    'timestamp': curr.timestamp
                                },
                                'node_lineage': curr.node_lineage
                            }
                            result.info.push(info);
                    };
                    """))


if __name__ == '__main__':
    main()
