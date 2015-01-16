import datetime
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from model import Subscription
from model import DigestNotification
from website import mails
from mako.lookup import Template


def notify(uid, event, **context):
    key = str(uid + '_' + event)

    for notification_type in notifications.keys():
        try:
            subscription = Subscription.find_one(Q('_id', 'eq', key))
        except NoResultsFound:
            return
        subscribed_users = []
        try:
            subscribed_users = getattr(subscription, notification_type)
        # TODO: handle this error
        except AttributeError:
            pass
        send(subscribed_users, notification_type, event, **context)


def send(subscribed_users, notification_type, event, **context):
    notifications.get(notification_type)(subscribed_users, event, **context)


def email_transactional(subscribed_users, event, **context):
    """
    :param subscribed_users:mod-odm User objects
    :param context: context variables for email template
    :return:
    """
    subject = Template(email_templates[event]['subject']).render(**context)
    message = Template(email_templates[event]['message']).render(**context)

    for user in subscribed_users:
        email = user.username
        if context.get('commenter') != user.fullname:
            mails.send_mail(
                to_addr=email,
                mail=mails.TRANSACTIONAL,
                name=user.fullname,
                subject=subject,
                message=message)


def email_digest(subscribed_users, event, **context):
    message = Template(email_templates[event]['message']).render(**context)

    for user in subscribed_users:
        if context.get('commenter') != user.fullname:
            digest = DigestNotification(timestamp=datetime.datetime.utcnow(),
                                        event=event,
                                        user_id=user._id,
                                        message=message)
            digest.save()


notifications = {
    'email_transactional': email_transactional,
    'email_digest': email_digest
}

email_templates = {
    'comments': {
        'subject': '${commenter} commented on "${title}".',
        'message': '${commenter} commented on your project "${title}": "${message}"'
    },
    'comment_replies': {
        'subject': '${commenter} replied to your comment on "${title}".',
        'message': '${commenter} replied to your comment "${parent_comment}" on your project "${title}": "${message}"'
    }
}


