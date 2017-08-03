import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.models import OSFUser
from osf.models.queued_mail import NO_LOGIN_TYPE, NO_LOGIN, QueuedMail, queue_mail
from website.app import init_app
from website import settings

from scripts.utils import add_file_logger

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    for user in find_inactive_users_with_no_inactivity_email_sent_or_queued():
        if dry_run:
            logger.warn('Dry run mode')
        logger.warn('Email of type no_login queued to {0}'.format(user.username))
        if not dry_run:
            with transaction.atomic():
                queue_mail(
                    to_addr=user.username,
                    mail=NO_LOGIN,
                    send_at=timezone.now(),
                    user=user,
                    fullname=user.fullname,
                )


def find_inactive_users_with_no_inactivity_email_sent_or_queued():
    users_sent_ids = QueuedMail.objects.filter(email_type=NO_LOGIN_TYPE).values_list('user__guids___id')
    return (OSFUser.objects
        .filter(
            (Q(date_last_login__lt=timezone.now() - settings.NO_LOGIN_WAIT_TIME) & ~Q(tags__name='osf4m')) |
            Q(date_last_login__lt=timezone.now() - settings.NO_LOGIN_OSF4M_WAIT_TIME, tags__name='osf4m'),
            is_active=True)
        .exclude(guids___id__in=users_sent_ids))

@celery_app.task(name='scripts.triggered_mails')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)
