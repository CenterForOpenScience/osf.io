import datetime
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from model import Subscription
from model import DigestNotification
from website import mails


# __inti__
# from ..methods.email import send_email_digest
# from ..methods.text import send_text_message


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
    for user in subscribed_users:
        email = user.username
        if context.get('commenter') != user.fullname:
            mails.send_mail(
                to_addr=email,
                mail=email_templates.get(event),
                user=user,
                name=user.fullname,
                commenter=context.get('commenter'),
                content=context.get('content'),
                parent_comment=context.get('parent_comment'),
                title=context.get('title'))


def email_digest(subscribed_users, event, **context):
    for user in subscribed_users:
        if context.get('commenter') != user.fullname:
            digest = DigestNotification(timestamp=datetime.datetime.utcnow(),
                                        event=event,
                                        user_id=user._id,
                                        context=context)
            digest.save()


notifications = {
    'email_transactional': email_transactional,
    'email_digest': email_digest
}

email_templates = {
    'Comments': mails.COMMENT_ADDED,
    'Comment_replies': mails.COMMENT_REPLIES
}


