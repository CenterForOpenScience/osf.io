import logging

from django.db import transaction
from django.utils import timezone

from website.prereg.utils import get_prereg_schema

from framework.celery_tasks import app as celery_app
from osf.models import DraftRegistration, QueuedMail
from osf.models.queued_mail import PREREG_REMINDER, PREREG_REMINDER_TYPE, queue_mail

from website.app import init_app
from website import settings

from scripts.utils import add_file_logger

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):

    for prereg in find_neglected_prereg_within_reminder_limit():
        if dry_run:
            logger.warn('Dry run mode')
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
                    project_name=prereg.branched_from.title,
                    draft_id=prereg._id,
                )

def find_neglected_prereg_within_reminder_limit():

    queue_data = QueuedMail.objects.filter(
        email_type=PREREG_REMINDER_TYPE,
        send_at__gte=timezone.now() - settings.PREREG_AGE_LIMIT,
        data__draft_id__isnull=False
    ).values_list('data', flat=True)

    already_queued = [entry['draft_id'] for entry in queue_data]

    return DraftRegistration.objects.filter(
        deleted__isnull=True,
        registered_node=None,
        registration_schema=get_prereg_schema(),
        datetime_initiated__lte=timezone.now()-settings.PREREG_WAIT_TIME,
        datetime_initiated__gte=timezone.now()-settings.PREREG_AGE_LIMIT,
    ).exclude(_id__in = already_queued)


@celery_app.task(name='scripts.remind_draft_preregistrations')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)

