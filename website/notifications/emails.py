from modularodm import Q
from model import Subscription
from framework.auth.core import User
from website import mails


def notify(pid, event, **context):
    key = str(pid + '_' + event)
    subscriber_emails = Subscription.find_one(Q('_id', 'eq', key)).types['email']
    send_email(subscriber_emails, **context)


def send_email(subscriber_emails, **context):
    for email in subscriber_emails:
        user = User.find_one(Q('username', 'eq', email))
        mails.send_mail(
            to_addr=email,
            mail=mails.COMMENT_ADDED,
            user=user,
            name=user.fullname,
            commenter=context.get('commenter'),
            content=context.get('content'),
            title=context.get('title'))