from modularodm import Q
from model import Subscription
from website import mails

# __inti__
# from ..methods.email import send_email_digest
# from ..methods.text import send_text_message


def notify(pid, event, **context):
    key = str(pid + '_' + event)

    for notification_type in notifications.keys():
        subscription = Subscription.find_one(Q('_id', 'eq', key))
        subscribed_users = []
        try:
            subscribed_users = getattr(subscription, notification_type)
        # TODO: handle this error
        except AttributeError:
            pass
        send(subscribed_users, notification_type, **context)


def send(subscribed_users, notification_type, **context):
    notifications.get(notification_type)(subscribed_users, **context)


def email_transactional(subscribed_users, **context):
    """
    :param subscribed_users:mod-odm User objects
    :param context: context variables for email template
    :return:
    """
    for user in subscribed_users:
        email = user.username
        if context.get('commenter') != user.fullname:

            mails.send_mail(
                to_addr=email,
                mail=mails.COMMENT_ADDED,
                user=user,
                name=user.fullname,
                commenter=context.get('commenter'),
                content=context.get('content'),
                parent_comment=context.get('parent_comment'),
                title=context.get('title'))

notifications = {
    'email_transactional': email_transactional
}


