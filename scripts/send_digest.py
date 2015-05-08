"""Script for sending OSF email digests to subscribed users and removing the records once sent."""

import datetime
import logging
from bson.code import Code

from modularodm import Q

from framework import sentry
from framework.auth.core import User
from framework.mongo import database as db
from framework.tasks import app as celery_app
from scripts import utils as script_utils
from website import mails
from website.app import init_app
from website.notifications.model import NotificationDigest
from website.notifications.utils import NotificationsDict
from website import settings


logger = logging.getLogger(__name__)
# Silence loud internal mail logger
SILENT_LOGGERS = [
    'website.mails',
    'amqp',
]
if not settings.DEBUG_MODE:
    for logger_name in SILENT_LOGGERS:
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def main():
    script_utils.add_file_logger(logger, __file__)
    app = init_app(attach_request_handlers=False)
    celery_app.main = 'scripts.send_digest'
    grouped_digests = group_digest_notifications_by_user()
    with app.test_request_context():
        send_digest(grouped_digests)


def send_digest(grouped_digests):
    """ Send digest emails and remove digests for sent messages in a callback.
    :param grouped_digests: digest notification messages from the past 24 hours grouped by user
    :return:
    """
    for group in grouped_digests:
        user = User.load(group['user_id'])
        if not user:
            sentry.log_exception()
            sentry.log_message("A user with this username does not exist.")
            return

        info = group['info']
        digest_notification_ids = [message['_id'] for message in info]
        sorted_messages = group_messages_by_node(info)

        if sorted_messages:
            logger.info('Sending email digest to user {0!r}'.format(user))
            mails.send_mail(
                to_addr=user.username,
                mimetype='html',
                mail=mails.DIGEST,
                name=user.fullname,
                message=sorted_messages,
                callback=remove_sent_digest_notifications.si(
                    digest_notification_ids=digest_notification_ids
                )
            )


@celery_app.task
def remove_sent_digest_notifications(digest_notification_ids=None):
    for digest_id in digest_notification_ids:
        NotificationDigest.remove(Q('_id', 'eq', digest_id))


def group_messages_by_node(notifications):
    d = NotificationsDict()
    for notification in notifications:
        d.add_message(notification['node_lineage'], notification['message'])
    return d


def group_digest_notifications_by_user():
    """ Group digest notification messages from the past 24 hours by user
    :return: [{
                'user_id': 'se8ea',
                'info': [{
                    'message': {
                        'message': 'Freddie commented on your project Open Science',
                        'timestamp': datetime object
                    },
                    'node_lineage': ['parent._id', 'node._id'],
                    '_id': NotificationDigest._id
                }, ...
                }]
              },
              {
                'user_id': ...
              }]
    """
    return db['notificationdigest'].group(
        key={'user_id': 1},
        condition={
            'timestamp': {
                '$lt': datetime.datetime.utcnow()
            }
        },
        initial={'info': []},
        reduce=Code(
            """
            function(curr, result) {
                result.info.push({
                    'message': curr.message,
                    'node_lineage': curr.node_lineage,
                    '_id': curr._id
                });
            };
            """
        )
    )


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
