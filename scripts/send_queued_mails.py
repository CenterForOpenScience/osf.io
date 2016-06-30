import logging

from datetime import datetime

from modularodm import Q

from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website import mails, settings

from scripts.utils import add_file_logger


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    # find all emails to be sent, pops the top one for each user(to obey the once
    # a week requirement), checks to see if one has been sent this week, and if
    # not send the email, otherwise leave it in the queue

    user_queue = {}
    for email in find_queued_mails_ready_to_be_sent():
        user_queue.setdefault(email.user._id, []).append(email)

    emails_to_be_sent = pop_and_verify_mails_for_each_user(user_queue)

    logger.info('Emails being sent at {0}'.format(datetime.utcnow().isoformat()))

    for mail in emails_to_be_sent:
        if not dry_run:
            with TokuTransaction():
                try:
                    sent_ = mail.send_mail()
                    message = 'Email of type {0} sent to {1}'.format(mail.email_type, mail.to_addr) if sent_ else \
                        'Email of type {0} failed to be sent to {1}'.format(mail.email_type, mail.to_addr)
                    logger.info(message)
                except Exception as error:
                    logger.error('Email of type {0} to be sent to {1} caused an ERROR'.format(mail.email_type, mail.to_addr))
                    logger.exception(error)
                    pass
        else:
            logger.info('Email of type {} will be sent to {}'.format(mail.email_type, mail.to_addr))


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


@celery_app.task(name='scripts.send_queued_mails')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)
