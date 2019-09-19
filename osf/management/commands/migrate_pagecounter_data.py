import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from framework import sentry
from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)


LIMIT_CLAUSE = ' LIMIT %s);'
NO_LIMIT_CLAUSE = ');'

REVERSE_SQL_BASE = '''
UPDATE osf_pagecounter PC
SET
    resource_id = NULL,
    file_id = NULL,
    version = NULL,
    action = NULL
WHERE PC.id IN (
    SELECT PC.id FROM osf_pagecounter PC
        INNER JOIN osf_guid Guid on Guid._id = split_part(PC._id, ':', 2)
        INNER JOIN osf_basefilenode File on File._id = split_part(PC._id, ':', 3)
'''
REVERSE_SQL = '{} {}'.format(REVERSE_SQL_BASE, NO_LIMIT_CLAUSE)
REVERSE_SQL_LIMITED = '{} {}'.format(REVERSE_SQL_BASE, LIMIT_CLAUSE)

FORWARD_SQL_BASE = '''
    UPDATE osf_pagecounter PC
    SET
        action = split_part(PC._id, ':', 1),
        resource_id = Guid.id,
        file_id = File.id,
        version = NULLIF(split_part(PC._id, ':', 4), '')::int
    FROM osf_guid Guid, osf_basefilenode File
        WHERE
              Guid._id = split_part(PC._id, ':', 2) AND
              File._id = split_part(PC._id, ':', 3) AND
              PC.id in (
                  select PC.id from osf_pagecounter PC
                      INNER JOIN osf_guid Guid on Guid._id = split_part(PC._id, ':', 2)
                      INNER JOIN osf_basefilenode File on File._id = split_part(PC._id, ':', 3)
                  WHERE (PC.resource_id IS NULL OR PC.file_id IS NULL)
'''
FORWARD_SQL = '{} {}'.format(FORWARD_SQL_BASE, NO_LIMIT_CLAUSE)
FORWARD_SQL_LIMITED = '{} {}'.format(FORWARD_SQL_BASE, LIMIT_CLAUSE)

COUNT_SQL = '''
SELECT count(PC.id)
    from osf_pagecounter as PC
    INNER JOIN osf_guid Guid on Guid._id = split_part(PC._id, ':', 2)
    INNER JOIN osf_basefilenode File on File._id = split_part(PC._id, ':', 3)
where (PC.resource_id IS NULL or PC.file_id IS NULL);
'''

@celery_app.task(name='management.commands.migrate_pagecounter_data')
def migrate_page_counters(dry_run=False, rows=10000, reverse=False):
    script_start_time = datetime.datetime.now()
    logger.info('Script started time: {}'.format(script_start_time))

    sql_query = REVERSE_SQL_LIMITED if reverse else FORWARD_SQL_LIMITED
    logger.info('SQL Query: {}'.format(sql_query))

    with connection.cursor() as cursor:
        if not dry_run:
            cursor.execute(sql_query, [rows])
        if not reverse:
            cursor.execute(COUNT_SQL)
            number_of_entries_left = cursor.fetchone()[0]
            logger.info('Entries left: {}'.format(number_of_entries_left))
            if number_of_entries_left == 0:
                sentry.log_message('Migrate pagecounter data complete')

    script_finish_time = datetime.datetime.now()
    logger.info('Script finished time: {}'.format(script_finish_time))
    logger.info('Run time {}'.format(script_finish_time - script_start_time))


class Command(BaseCommand):
    help = '''Does the work of the pagecounter migration so that it can be done incrementally when convenient.
    You will either need to set the page_size large enough to get all of the records, or you will need to run the
    script multiple times until it tells you that it is done.'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not write files',
        )
        parser.add_argument(
            '--rows',
            type=int,
            default=10000,
            help='How many rows to process during this run',
        )
        parser.add_argument(
            '--reverse',
            type=bool,
            default=False,
            help='Reverse out the migration',
        )

    # Management command handler
    def handle(self, *args, **options):
        logger.debug(options)

        dry_run = options['dry_run']
        rows = options['rows']
        reverse = options['reverse']
        logger.debug(
            'Dry run: {}, rows: {}, reverse: {}'.format(
                dry_run,
                rows,
                reverse,
            )
        )
        if dry_run:
            logger.info('DRY RUN')

        migrate_page_counters(dry_run, rows, reverse)
