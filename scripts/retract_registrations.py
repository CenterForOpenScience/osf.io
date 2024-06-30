"""Script for retracting pending retractions that are more than 48 hours old."""
import sys
import logging

import django
from django.db import transaction
from django.utils import timezone
django.setup()

from framework import sentry
from framework.celery_tasks import app as celery_app

from website.app import init_app
from website import settings
from osf.models import Retraction

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_retractions = Retraction.objects.filter(state=Retraction.UNAPPROVED)
    for retraction in pending_retractions:
        if should_be_retracted(retraction):
            if dry_run:
                logger.warning('Dry run mode')
            try:
                parent_registration = retraction.registrations.get()
            except Exception as err:
                logger.exception(f'Could not find registration associated with retraction {retraction}')
                logger.error(f'Skipping...')
                sentry.log_message(str(err))
                continue

            logger.warning(
                f'Retraction {retraction._id} approved. Retracting registration {parent_registration._id}'
            )
            if not dry_run:
                sid = transaction.savepoint()
                try:
                    retraction.accept()
                    transaction.savepoint_commit(sid)
                except Exception as err:
                    logger.error(
                        f'Unexpected error raised when retracting '
                        f'registration {parent_registration._id}. Continuing...'
                    )
                    logger.exception(err)
                    sentry.log_message(str(err))
                    transaction.savepoint_rollback(sid)


def should_be_retracted(retraction):
    """Returns true if retraction was initiated more than 48 hours prior"""
    return (timezone.now() - retraction.initiation_date) >= settings.RETRACTION_PENDING_TIME


@celery_app.task(name='scripts.retract_registrations')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    main(dry_run=dry_run)


if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
