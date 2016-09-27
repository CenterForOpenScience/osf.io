import logging

from datetime import datetime

from modularodm import Q

from framework.auth import User
from framework.celery_tasks import app as celery_app
from framework.transactions.context import TokuTransaction

from website.app import init_app
from website import mails, settings

from scripts.utils import add_file_logger

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
                    fullname=user.fullname,
                )


def find_inactive_users_with_no_inactivity_email_sent_or_queued():
    inactive_users = User.find(
        (Q('date_last_login', 'lt', datetime.utcnow() - settings.NO_LOGIN_WAIT_TIME) & Q('osf4m', 'ne', 'system_tags')) |
        (Q('date_last_login', 'lt', datetime.utcnow() - settings.NO_LOGIN_OSF4M_WAIT_TIME) & Q('osf4m', 'eq', 'system_tags'))
    )
    inactive_emails = mails.QueuedMail.find(Q('email_type', 'eq', mails.NO_LOGIN_TYPE))

    #This is done to prevent User query returns comparison to User, as equality fails
    #on datetime fields due to pymongo rounding. Instead here _id is compared.
    users_sent_id = [email.user._id for email in inactive_emails]
    inactive_ids = [user._id for user in inactive_users if user.is_active]
    users_to_send = [User.load(id) for id in (set(inactive_ids) - set(users_sent_id))]
    return users_to_send


@celery_app.task(name='scripts.triggered_mails')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)

