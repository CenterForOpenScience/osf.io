import datetime
from modularodm import Q
from modularodm.exceptions import NoResultsFound
from model import Subscription
from model import DigestNotification
from website import mails
from framework.auth.core import User
from framework.mongo import database as db
from bson.code import Code

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
                name=user.fullname,
                commenter=context.get('commenter'),
                title=context.get('title'),
                context_vars=context)


def email_digest(subscribed_users, event, **context):
    for user in subscribed_users:
        if context.get('commenter') != user.fullname:
            message = build_content_from_template(event, **context)

            digest = DigestNotification(timestamp=datetime.datetime.utcnow(),
                                        event=event,
                                        user_id=user._id,
                                        context=message)
            digest.save()

    send_digest()


def send_digest():
    grouped_digests = group_digest_notifications_by_user()

    for group in grouped_digests:
        try:
            user = User.find_one(Q('_id', 'eq', group['user_id']))
        except NoResultsFound:
            # ignore for now, but raise error here
            user = None

        messages = group['messageContexts']
        if user and messages:
            mails.send_mail(
                to_addr=user.username,
                mail=email_templates.get('Digest'),
                name=user.fullname,
                content=messages)


def group_digest_notifications_by_user():
    return db['digestnotification'].group(
        key={'user_id': 1},
        condition={'timestamp': {'$lt': datetime.datetime.utcnow(), '$gte': datetime.datetime.utcnow()-datetime.timedelta(hours=24)}},
        initial={'messageContexts': []},
        reduce=Code("""function(curr, result) {
                            result.messageContexts.push(curr.context);
                    };
                    """))


def build_content_from_template(event, **context):
    for key in email_templates.keys():
        if key == event:
            return email_templates[event].text(context_vars=context)


notifications = {
    'email_transactional': email_transactional,
    'email_digest': email_digest
}

email_templates = {
    'Comments': mails.COMMENT_ADDED,
    'Comment_replies': mails.COMMENT_REPLIES,
    'Digest': mails.DIGEST
}


