import logging

from django.db import transaction
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from osf.models import DraftRegistration, MetaSchema, QueuedMail
from osf.models.queued_mail import PREREG_REMINDER, PREREG_REMINDER_TYPE, queue_mail

from website.app import init_app
from website import settings

from scripts.utils import add_file_logger

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):

    user_email_counts = get_user_email_counts()
    for prereg in find_neglected_prereg_within_reminder_limit():
        logger.warn(len(find_neglected_prereg_within_reminder_limit()))
        if dry_run:
            logger.warn('Dry run mode')
        user_email_counts[prereg.initiator.id] = user_email_counts.get(prereg.initiator.id, 0)
        if user_email_counts[prereg.initiator.id] < settings.MAX_PREREG_REMINDER_EMAILS:
            logger.info('Email of type prereg_reminder queued to send to {0}'.format(prereg.initiator.username))
            if not dry_run:
                with transaction.atomic():
                    queue_mail(
                        to_addr=prereg.initiator.username,
                        mail=PREREG_REMINDER,
                        send_at=timezone.now(),
                        user=prereg.initiator,
                        fullname=prereg.initiator.fullname,
                        prereg_url=prereg.absolute_url,
                        draft_id=prereg._id,
                    )

            user_email_counts[prereg.initiator.id] += 1

def find_neglected_prereg_within_reminder_limit():

    return DraftRegistration.objects.filter(
        reminder_sent=False,
        approval__isnull=True,
        registration_schema=MetaSchema.objects.get(name='Prereg Challenge'),
        datetime_initiated__lte=timezone.now()-settings.PREREG_WAIT_TIME,
        datetime_initiated__gte=timezone.now()-settings.PREREG_AGE_LIMIT
    )

def get_user_email_counts():
    users_sent_ids = QueuedMail.objects.filter(
        email_type = PREREG_REMINDER_TYPE,
        send_at__gt = timezone.now() - settings.PREREG_WAIT_TIME
    ).values_list('user__guids___id')

    user_email_counts = dict()
    for id in users_sent_ids:
        user_email_counts[id] = user_email_counts.get(id, 0) + 1

    return user_email_counts


@celery_app.task(name='scripts.remind_draft_preregistrations')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)

