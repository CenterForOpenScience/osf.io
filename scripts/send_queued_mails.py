import sys
import logging
from datetime import datetime, timedelta

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website import mails, settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main(dry_run=True):
    #find all emails to be sent, pops the top one for each user(to obey the once
    #a week requirement), checks to see if one has been sent this week, and if
    #not send the email, otherwise leave it in the queue

    user_queue = {}
    for email in find_queued_mails_ready_to_be_sent():
        user_queue.setdefault(email.user._id, []).append(email)

    emails_to_be_sent = pop_and_verify_mails_for_each_user(user_queue)

    for mail in emails_to_be_sent:
        logger.warn('Email of type {0} sent to {1}'.format(mail.email_type, mail.to_addr))
        if dry_run:
            logger.warn('Dry run mode')
        else:
            with TokuTransaction():
                mail.send_mail()

def find_queued_mails_ready_to_be_sent():
    return mails.QueuedMail.find(
        Q('send_at', 'lt', datetime.utcnow()) &
        Q('sent_at', 'eq', None)
    )

def pop_and_verify_mails_for_each_user(user_queue):
    for user_emails in user_queue.values():
        mail = user_emails[0]
        mails_past_week = mails.QueuedMail.find(
            Q('user', 'eq', mail.user) &
            Q('sent_at', 'gt', datetime.utcnow() - settings.WAIT_BETWEEN_MAILS)
        )
        if not mails_past_week.count():
            yield mail

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    init_app(routes=False)
    main(dry_run=dry_run)
