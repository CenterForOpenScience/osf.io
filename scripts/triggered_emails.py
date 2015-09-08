import sys
import logging
from datetime import datetime, timedelta

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website import mails
from framework.auth import User

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main(dry_run=True):
    #one query for 6 weeks and osf4m users, and one for 4 weeks for regular users
    inactive_users = list(User.find(Q('date_last_login', 'lt', datetime.utcnow() - timedelta(weeks=4)) &
                                    Q('conference_user', 'eq', False)))
    inactive_users.extend(list(User.find(Q('date_last_login', 'lt', datetime.utcnow() - timedelta(weeks=6)) &
                                    Q('conference_user', 'eq', True))))
    inactive_emails = list(mails.QueuedMail.find(Q('email_type', 'eq', 'no_login')))
    users_sent = []
    for email in inactive_emails:
        users_sent.append(email.user)
    for user in set(inactive_users) - set(users_sent):
        if dry_run:
            logger.warn('Dry run mode')
            logger.warn('Queueing up no_login email to {0}'.format(user.username))
        if not dry_run:
            with TokuTransaction():
                mails.queue_mail(
                    to_addr=user.username,
                    mail=mails.NO_LOGIN,
                    send_at=datetime.utcnow(),
                    user=user,
                    fullname=user.fullname
                )

    #find all emails to be sent, pops the top one for each user(to obey the once
    #a week requirement), checks to see if one has been sent this week, and if
    #not send the email, otherwise leave it in the queue
    queued_emails = list(mails.QueuedMail.find(
        Q('send_at', 'lt', datetime.utcnow()) &
        Q('sent_at', 'eq', None)
    ))

    user_queue = {}
    for email in queued_emails:
        user_queue.setdefault(email.user._id, []).append(email)

    for user in user_queue.values():
        mail = user[0]
        mails_past_week = list(mails.QueuedMail.find(
            Q('user', 'eq', mail.user) &
            Q('sent_at', 'gt', datetime.utcnow() - timedelta(days=7))
        ))
        if not len(mails_past_week):
            if dry_run:
                logger.warn('Dry run mode')
                logger.warn('Email of type {0} sent to {1}'.format(mail.email_type, mail.to_addr))
            with TokuTransaction():
                mail.send_mail()

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    main(dry_run=dry_run)
