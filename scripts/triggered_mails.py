import sys
import logging
from datetime import datetime, timedelta

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website import mails, settings
from framework.auth import User

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main(dry_run=True):
    for user in find_inactive_users_with_no_inactivity_email_sent_or_queued():
        if dry_run:
            logger.warn('Dry run mode')
        logger.warn('Email of type no_login queued to {0}'.format(user.username))
        if not dry_run:
            with TokuTransaction():
                mails.queue_mail(
                    to_addr=user.username,
                    mail=mails.NO_LOGIN,
                    send_at=datetime.utcnow(),
                    user=user,
                    fullname=user.fullname
                )

def find_inactive_users_with_no_inactivity_email_sent_or_queued():
    #one query for 6 weeks and osf4m users, and one for 4 weeks for regular users
    inactive_users = list(User.find(Q('date_last_login', 'lt', datetime.utcnow() - settings.NO_LOGIN_WAIT_TIME) &
                                    Q('is_conference_user', 'eq', False)))
    inactive_users.extend(list(User.find(Q('date_last_login', 'lt', datetime.utcnow() - settings.NO_LOGIN_OSF4M_WAIT_TIME) &
                                    Q('is_conference_user', 'eq', True))))
    inactive_emails = list(mails.QueuedMail.find(Q('email_type', 'eq', 'no_login')))
    users_sent = []
    for email in inactive_emails:
        users_sent.append(email.user)
    return set(inactive_users) - set(users_sent)

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    main(dry_run=dry_run)
