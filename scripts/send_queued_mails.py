import logging

import django
from django.db import transaction
from django.utils import timezone
django.setup()

from framework.celery_tasks import app as celery_app

from osf.models.queued_mail import QueuedMail
from website.app import init_app
from website import settings

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

    logger.info(f'Emails being sent at {timezone.now().isoformat()}')

    for mail in emails_to_be_sent:
        if not dry_run:
            with transaction.atomic():
                try:
                    sent_ = mail.send_mail()
                    message = f'Email of type {mail.email_type} sent to {mail.to_addr}' if sent_ else \
                        f'Email of type {mail.email_type} failed to be sent to {mail.to_addr}'
                    logger.info(message)
                except Exception as error:
                    logger.error(f'Email of type {mail.email_type} to be sent to {mail.to_addr} caused an ERROR')
                    logger.exception(error)
                    pass
        else:
            logger.info(f'Email of type {mail.email_type} will be sent to {mail.to_addr}')


def find_queued_mails_ready_to_be_sent():
    return QueuedMail.objects.filter(send_at__lt=timezone.now(), sent_at__isnull=True)

def pop_and_verify_mails_for_each_user(user_queue):
    for user_emails in user_queue.values():
        mail = user_emails[0]
        mails_past_week = mail.user.queuedmail_set.filter(sent_at__gt=timezone.now() - settings.WAIT_BETWEEN_MAILS)
        if not mails_past_week.count():
            yield mail


@celery_app.task(name='scripts.send_queued_mails')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)
