"""Script for sending OSF email digests to subscribed users and removing the records once sent."""

import datetime
import logging
from bson.code import Code

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework import sentry
from framework.auth.core import User
from framework.mongo import database as db
from framework.tasks import app as celery_app
from scripts import utils as script_utils
from website import mails
from website.app import init_app
from website.util import web_url_for
from website.notifications.model import DigestNotification
from website.notifications.utils import NotificationsDict


logger = logging.getLogger(__name__)


def main():
    script_utils.add_file_logger(logger, __file__)
    app = init_app()
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
                callback=remove_sent_digest_notifications.s(digest_notification_ids=digest_notification_ids)
            )

@celery_app.task
def remove_sent_digest_notifications(ret=None, digest_notification_ids=None):
    for digest_id in digest_notification_ids:
        DigestNotification.remove(Q('_id', 'eq', digest_id))


def group_messages_by_node(notifications):
    d = NotificationsDict()
    for n in notifications:
        d.add_message(n['node_lineage'], n['message'])
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
                    '_id': DigestNotification._id
                }, ...
                }]
              },
              {
                'user_id': ...
              }]
    """
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
    logging.basicConfig(level=logging.DEBUG)
    main()