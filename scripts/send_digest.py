"""Script for sending OSF email digests to subscribed users and removing the records once sent."""

import logging
import datetime
from bson.code import Code
from functools import partial
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from framework import sentry
from framework.auth.core import User
from framework.mongo import database as db
from website import mails
from website.util import web_url_for
from website.app import init_app
from website.notifications.model import DigestNotification
from website.notifications.utils import NotificationsDict

from scripts import utils as script_utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def main():
    script_utils.add_file_logger(logger, __file__)
    app = init_app()
    grouped_digests = group_digest_notifications_by_user()
    with app.test_request_context():
        send_digest(grouped_digests)

#TODO: Add tests for callback and removing digest notification records
def send_digest(grouped_digests):
    for group in grouped_digests:
        try:
            user = User.load(group['user_id'])
        except NoResultsFound:
            sentry.log_exception()
            sentry.log_message("A user with this username does not exist.")
            user = None

        info = group['info']
        digest_notification_ids = [message['_id'] for message in info]
        sorted_messages = group_messages_by_node(info)

        if user and sorted_messages:
            logger.info('Sending email digest to user {0!r}'.format(user))
            mails.send_mail(
                to_addr=user.username,
                mimetype='html',
                mail=mails.DIGEST,
                name=user.fullname,
                message=sorted_messages,
                url=web_url_for('user_notifications', _absolute=True),
                callback=partial(remove_sent_digest_notifications,
                                 digest_notification_ids=digest_notification_ids)
            )


def remove_sent_digest_notifications(digest_notification_ids):
    DigestNotification.remove(Q('_id', 'eq', digest_notification_ids))


def group_messages_by_node(notifications):
    d = NotificationsDict()
    for n in notifications:
        d.add_message(n['node_lineage'], n['message'])
    return d


def group_digest_notifications_by_user():
    return db['digestnotification'].group(
        key={'user_id': 1},
        condition={'timestamp': {'$lt': datetime.datetime.utcnow(),
                                 '$gte': datetime.datetime.utcnow() - datetime.timedelta(hours=24)}},
        initial={'info': []},
        reduce=Code("""function(curr, result) {
                            info = {
                                'message': {
                                    'message': curr.message,
                                    'timestamp': curr.timestamp
                                },
                                'node_lineage': curr.node_lineage,
                                '_id': curr._id
                            }
                            result.info.push(info);
                    };
                    """))


if __name__ == '__main__':
    main()