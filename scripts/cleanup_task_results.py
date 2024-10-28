import logging
import sys
import datetime

from django.db import transaction
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from scripts.utils import add_file_logger

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

from website.app import setup_django
setup_django()
from django_celery_results.models import TaskResult

TASK_RESULT_AGE_THRESHOLD = 30

def main(dry_run=True):
    cutoff_date = timezone.now() - datetime.timedelta(days=TASK_RESULT_AGE_THRESHOLD)

    if dry_run:
        logger.warn('Dry run mode, will delete task results and then abort the transaction')
    logger.info('Preparing to delete TaskResult objects older than {} days'.format(TASK_RESULT_AGE_THRESHOLD))

    with transaction.atomic():
        count, _ = TaskResult.objects.filter(date_done__lt=cutoff_date).delete()
        logger.info('Deleted {} TaskResult objects'.format(count))

        if dry_run:
            raise Exception('Dry run, aborting the transaction!')


@celery_app.task(name='scripts.cleanup_task_results')
def run_main(dry_run=True):
    if not dry_run:
        add_file_logger(logger, __file__)
    main(dry_run=dry_run)


if __name__ == '__main__':
    run_main(dry_run='--dry' in sys.argv)
