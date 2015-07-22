"""
Tasks for making even transactional emails consolidated.
"""

from datetime import datetime, timedelta
from bson.code import Code
from modularodm import Q

from framework.tasks import app as celery_app
from framework.mongo import database as db
from framework.auth.core import User

from website.notifications.utils import NotificationsDict
from website.notifications.model import NotificationDigest
from website import mails


# TODO: Not sure whether to make this a class and use some of the same ideas as archives/tasks
# http://blog.miguelgrinberg.com/post/using-celery-with-flask


def check_and_send_later(user, time_start, time_to_send, delay_type):
    """
    Checks for a task already pending for a user. If no user then start a new task.
    :param user:
    :return:
    """
    if not isinstance(user, User):
        task_id = user + '_' + delay_type
    else:
        task_id = user._id + '_' + delay_type
    celery_app.main = 'website.notifications.tasks'
    task = None
    try:
        task = send_user_email.Async_Result(task_id)
    except:
        pass
    if task and task.state == 'PENDING':
        print task.get()
    else:
        send_user_email.apply_async(args=(user, time_start), eta=time_to_send)
    print "We are here."


@celery_app.task(name='notify.send_user_email', max_retries=0)
def send_user_email(user, time_start):
    """
    Finds pending Emails and amalgamates them into a single Email
    :param user: User to send mails to.
    :return:
    """
    if not isinstance(user, User):
        user = User.load(user)
    emails = get_user_emails(user._id, time_start)
    if not emails:
        return
    info = emails[0]['info']
    notification_ids = [message['_id'] for message in info]
    grouped_emails = group_by_node(info)
    if grouped_emails:
        mails.send_mail(
            to_addr=user.username,
            mimetype='html',
            mail=mails.DIGEST,
            name=user.fullname,
            message=grouped_emails,
            callback=remove_notifications.si(email_notification_ids=notification_ids)
        )


def get_user_emails(user, time_start):
    """
    Get all emails that need to be sent within a window from start time to current
    :param user: user to send emails to
    :return:
    """
    time_current = datetime.utcnow() + timedelta(seconds=10)  # A bit of leeway
    return db['notificationdigest'].group(
        key={'user_id': 1},
        condition={
            'user_id': user,
            'timestamp': {
                '$lt': time_current
            },
            'time_to_send': {
                '$lt': time_current,
                '$gte': time_start
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


@celery_app.task
def remove_notifications(email_notification_ids=None):
    """
    Removes emails that were sent
    :param email_notification_ids:
    :return:
    """
    for email_id in email_notification_ids:
        NotificationDigest.remove(Q('_id', 'eq', email_id))
