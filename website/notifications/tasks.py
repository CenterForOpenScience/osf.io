"""
Tasks for making even transactional emails consolidated.
"""
from bson.code import Code
from modularodm import Q

from framework.celery_tasks import app as celery_app
from framework.mongo import database as db
from framework.auth.core import User
from framework.sentry import log_exception

from framework.transactions.context import TokuTransaction

from website.notifications.utils import NotificationsDict
from website.notifications.model import NotificationDigest
from website import mails


@celery_app.task(name='website.notifications.tasks.send_users_email', max_retries=0)
def send_users_email(send_type):
    """Find pending Emails and amalgamates them into a single Email.

    :param send_type
    :return:
    """
    grouped_emails = get_users_emails(send_type)
    if not grouped_emails:
        return
    for group in grouped_emails:
        user = User.load(group['user_id'])
        if not user:
            log_exception()
            continue
        info = group['info']
        notification_ids = [message['_id'] for message in info]
        sorted_messages = group_by_node(info)
        if sorted_messages:
            mails.send_mail(
                to_addr=user.username,
                mimetype='html',
                mail=mails.DIGEST,
                name=user.fullname,
                message=sorted_messages,
                callback=remove_notifications(email_notification_ids=notification_ids)
            )


def get_users_emails(send_type):
    """Get all emails that need to be sent.

    :param send_type: from NOTIFICATION_TYPES
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
    with TokuTransaction():
        emails = db['notificationdigest'].group(
            key={'user_id': 1},
            condition={
                'send_type': send_type
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
    return emails


def group_by_node(notifications):
    """Take list of notifications and group by node.

    :param notifications: List of stored email notifications
    :return:
    """
    emails = NotificationsDict()
    for notification in notifications:
        emails.add_message(notification['node_lineage'], notification['message'])
    return emails


def remove_notifications(email_notification_ids=None):
    """Remove sent emails.

    :param email_notification_ids:
    :return:
    """
    for email_id in email_notification_ids:
        NotificationDigest.remove(Q('_id', 'eq', email_id))
