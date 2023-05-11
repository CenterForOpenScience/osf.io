"""Script for retracting pending retractions that are more than 48 hours old."""
import sys
import logging

import django
from django.db import transaction
from django.utils import timezone
django.setup()

from framework.auth import Auth
from framework.celery_tasks import app as celery_app

from website.app import init_app
from website import settings
from osf.models import NodeLog, Retraction, Registration

from scripts import utils as scripts_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main(dry_run=True):
    pending_retractions = Retraction.objects.filter(state=Retraction.UNAPPROVED)
    for retraction in pending_retractions:
        if should_be_retracted(retraction):
            if dry_run:
                logger.warn('Dry run mode')
                parent_registration = retraction.registrations.get()

            logger.warn(
                'Retraction {0} approved. Retracting registration {1}'
                .format(retraction._id, parent_registration._id)
            )
            if not dry_run:
                with transaction.atomic():
                    retraction.accept()


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
