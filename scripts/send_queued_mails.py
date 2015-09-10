import sys
import logging
from datetime import datetime, timedelta

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website import mails

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main(dry_run=True):
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
