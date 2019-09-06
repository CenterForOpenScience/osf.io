import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from framework.celery_tasks import app as celery_app
from framework import sentry

logger = logging.getLogger(__name__)

DEBUG_PAGE_SIZE = 100000

TABLES_TO_POPULATE_WITH_MODIFIED = [
    'osf_comment',
    'osf_institution',
    'osf_privatelink'
]

POPULATE_COLUMNS = [
    """UPDATE osf_basefilenode SET deleted = deleted_on
    WHERE id IN (SELECT id FROM osf_basefilenode WHERE deleted_on IS NOT NULL AND deleted IS NULL LIMIT {})
    RETURNING id;""",
    """UPDATE osf_abstractnode SET deleted = CASE WHEN deleted_date IS NOT NULL THEN deleted_date ELSE last_logged END
    WHERE id IN (SELECT id FROM osf_abstractnode WHERE is_deleted AND deleted IS NULL LIMIT {})
    RETURNING id;"""
]

UPDATE_DELETED_WITH_MODIFIED = """UPDATE {} SET deleted=modified
WHERE id IN (SELECT id FROM {} WHERE is_deleted AND deleted IS NULL LIMIT {}) RETURNING id;"""

CHECK_POPULATED = """SELECT deleted, is_deleted FROM {} WHERE deleted IS NULL AND is_deleted ;"""

FORWARD_BASE_FILE = POPULATE_COLUMNS[0].format(DEBUG_PAGE_SIZE)
FORWARD_ABSTRACT_NODE = POPULATE_COLUMNS[1].format(DEBUG_PAGE_SIZE)

REVERSE_BASE_FILE = 'UPDATE osf_basefilenode SET deleted = null where deleted_on IS NOT NULL'
REVERSE_ABSTRACT_NODE = 'UPDATE osf_abstractnode SET deleted = null WHERE deleted_date IS NOT NULL'

FORWARD_COMMENT = UPDATE_DELETED_WITH_MODIFIED.format('osf_comment', 'osf_comment', DEBUG_PAGE_SIZE)
FORWARD_INSTITUTION = UPDATE_DELETED_WITH_MODIFIED.format('osf_institution', 'osf_institution', DEBUG_PAGE_SIZE)
FORWARD_PRIVATE_LINK = UPDATE_DELETED_WITH_MODIFIED.format('osf_privatelink', 'osf_privatelink', DEBUG_PAGE_SIZE)

REVERSE_COMMENT = 'UPDATE osf_basefilenode SET deleted = null where is_deleted'
REVERSE_INSTITUTION = 'UPDATE osf_institution SET deleted = null where is_deleted'
REVERSE_PRIVATE_LINK = 'UPDATE osf_privatelink SET deleted = null where is_deleted'

@celery_app.task(name='management.commands.migrate_deleted_date')
def populate_deleted(dry_run=False, page_size=1000):
    with transaction.atomic():
        for table in TABLES_TO_POPULATE_WITH_MODIFIED:
            run_statements(UPDATE_DELETED_WITH_MODIFIED, page_size, table)
        for statement in POPULATE_COLUMNS:
            run_sql(statement, page_size)
        if dry_run:
            raise RuntimeError('Dry Run -- Transaction rolled back')

def run_statements(statement, page_size, table):
    sentry.log_message('Populating deleted column in table {}'.format(table))
    with connection.cursor() as cursor:
        cursor.execute(CHECK_POPULATED.format(table), [page_size])
        rows = cursor.fetchall()
        if not rows:
            return
        cursor.execute(statement.format(table, table, page_size))
        rows = cursor.fetchall()
        if not rows:
            sentry.log_message('Deleted field in {} table is populated'.format(table))

def run_sql(statement, page_size):
    table = statement.split(' ')[1]
    sentry.log_message('Populating deleted column in table {}'.format(table))

    with connection.cursor() as cursor:
        cursor.execute(statement.format(page_size))
        rows = cursor.fetchall()
        if not rows:
            sentry.log_message('Deleted field in {} table is populated'.format(table))

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
            default=5000,
            help='How many rows to process at a time',
        )

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        sentry.log_message('Script started time: {}'.format(script_start_time))
        logger.debug(options)

        dry_run = options['dry_run']
        page_size = options['page_size']

        if dry_run:
            sentry.log_message('DRY RUN')

        populate_deleted(dry_run, page_size)

        script_finish_time = datetime.datetime.now()
        sentry.log_message('Script finished time: {}'.format(script_finish_time))
        sentry.log_message('Run time {}'.format(script_finish_time - script_start_time))
