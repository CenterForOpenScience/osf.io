import logging
import datetime

from django.core.management.base import BaseCommand
from framework.celery_tasks import app as celery_app
from django.db import connection, transaction

logger = logging.getLogger(__name__)

POPULATE_BRANCHED_FROM_NODE = """UPDATE osf_abstractnode a
 SET branched_from_node = CASE WHEN
    EXISTS(SELECT id FROM osf_nodelog WHERE action='project_created_from_draft_reg' AND node_id = a.id) THEN False
    ELSE True
END
WHERE
a.type = 'osf.registration' AND
a.branched_from_node IS null
"""

@celery_app.task(name='management.commands.populate_branched_from')
def populate_branched_from(page_size, dry_run):
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(POPULATE_BRANCHED_FROM_NODE, [page_size])
        if dry_run:
            raise RuntimeError('Dry Run -- Transaction rolled back')

class Command(BaseCommand):
    help = '''Populates new deleted field for various models. Ensure you have run migrations
    before running this script.'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not write files',
        )
        parser.add_argument(
            '--page_size',
            type=int,
            default=10000,
            help='How many rows to process at a time',
        )

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        logger.debug(options)

        dry_run = options['dry_run']
        page_size = options['page_size']

        if dry_run:
            logger.info('DRY RUN')

        populate_branched_from(page_size, dry_run)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
