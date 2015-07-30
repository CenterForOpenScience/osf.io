"""
Tasks for making even transactional emails consolidated.
"""

from datetime import datetime, timedelta
import time
from bson.code import Code
from modularodm import Q

from celery.exceptions import TimeoutError

from framework.tasks import app as celery_app
from framework.mongo import database as db
from framework.auth.core import User

from framework.transactions.context import TokuTransaction

from website.notifications.utils import NotificationsDict
from website.notifications.model import NotificationDigest
from website import mails


# TODO: Not sure whether to make this a class and use some of the same ideas as archives/tasks
# http://blog.miguelgrinberg.com/post/using-celery-with-flask


def check_and_send_later(user, time_start, time_to_send, send_type):
    """
    Checks for a task already pending for a user. If no user then start a new task.
    :param user:
    :return:
    """
    try:
        user_id = user._id  # better than isinstance
    except AttributeError:
        user_id = user
    task_id = user_id + '_' + send_type
    celery_app.main = 'website.notifications.tasks'
    try:
        task = send_user_email.AsyncResult(task_id)
        task.get(timeout=0.001)
    except TimeoutError:
        task = None
    if task is None or task.state == 'SUCCESS' or task.state == 'FAILURE':
        send_user_email.apply_async(args=(user_id, send_type), eta=time_to_send, task_id=task_id)
    else:
        print task.state

        # send_user_email.apply(args=(user, time_start), eta=time_to_send, task_id=task_id) #debug
        # send_user_email(user_id, time_start)


@celery_app.task(name='notify.send_user_email', max_retries=0)
def send_user_email(user_id, send_type):
    """
    Finds pending Emails and amalgamates them into a single Email
    :param user_id: User id to send mails to.
    :return:
    """
    count = 0
    for i in range(5):
        current_count = get_email_count(user_id, send_type)
        if count == current_count:
            break
        count = current_count
        time.sleep(60)
    emails = get_user_emails(user_id, send_type)
    if not emails:
        return
    info = emails[0]['info']
    notification_ids = [message['_id'] for message in info]
    grouped_emails = group_by_node(info)
    user = User.load(user_id)
    if grouped_emails:
        mails.send_mail(
            to_addr=user.username,
            mimetype='html',
            mail=mails.DIGEST,
            name=user.fullname,
            message=grouped_emails,
            callback=remove_notifications(email_notification_ids=notification_ids)
        )


def get_email_count(user, send_type):
    """
    Gets the number of emails that a user would receive if sent now.
    :param user:
    :return:
    """
    with TokuTransaction():
        count = db['notificationdigest'].find(
            {
                'user_id': user,
                'send_type': send_type
            }).count()
    return count


def get_user_emails(user, send_type):
    """
    Get all emails that need to be sent within a window from start time to current
    :param user: user to send emails to
    :return:
    """
    with TokuTransaction():
        emails = db['notificationdigest'].group(
            key={'user_id': 1},
            condition={
                'user_id': user,
                'send_type': send_type,
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
    """
    Takes list of notifications and groups by node.
    :param notifications: List of stored email notifications
    :return:
    """
    emails = NotificationsDict()
    for notification in notifications:
        emails.add_message(notification['node_lineage'], notification['message'])
    return emails


def remove_notifications(email_notification_ids=None):
    """
    Removes emails that were sent
    :param email_notification_ids:
    :return:
    """
    for email_id in email_notification_ids:
        NotificationDigest.remove(Q('_id', 'eq', email_id))
