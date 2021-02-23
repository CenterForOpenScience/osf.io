import logging
import django
django.setup()

from framework.celery_tasks import app as celery_app
from osf.models import Registration
from website import settings
from osf.utils.requests import requests_retry_session

logger = logging.getLogger(__name__)


@celery_app.task(name='scripts.migration.archive_registrations_on_IA')
def run_main(dry_run=False):
    registrations = Registration.objects.filter(IA_url__isnull=True)[:100]

    logger.info(f'{registrations.count()} to be archived in batch')

    for registration in registrations:
        if not dry_run:
            logger.info(f'archiving {registration._id}')
            requests_retry_session().post(f'{settings.OSF_PIGEON_URL}archive/{registration._id}')
        else:
            logger.info(f'DRY RUN for archiving {registration._id}')


if __name__ == '__main__':
    run_main()
