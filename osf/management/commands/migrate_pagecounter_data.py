import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

from framework import sentry

logger = logging.getLogger(__name__)


LIMIT_CLAUSE = ' LIMIT %s);'
NO_LIMIT_CLAUSE = ');'

REVERSE_SQL_BASE = '''
UPDATE osf_pagecounter PC
SET
    resource_id = NULL,
    file_id = NULL,
    version = NULL
WHERE PC.id in (
    select PC.id from osf_pagecounter PC
        left outer join osf_guid Guid on Guid._id = split_part(PC._id, ':', 2)
        left outer join osf_basefilenode File on File._id = split_part(PC._id, ':', 3)
    where
          resource_id IS NOT NULL OR
          file_id IS NOT NULL AND
          Guid._id IS NOT NULL AND File._id IS NOT NULL
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
                      left outer join osf_guid Guid on Guid._id = split_part(PC._id, ':', 2)
                      left outer join osf_basefilenode File on File._id = split_part(PC._id, ':', 3)
                  where (PC.resource_id is NULL or PC.file_id IS NULL) AND
                        Guid._id IS NOT NULL AND File._id IS NOT NULL
'''
FORWARD_SQL = '{} {}'.format(FORWARD_SQL_BASE, NO_LIMIT_CLAUSE)
FORWARD_SQL_LIMITED = '{} {}'.format(FORWARD_SQL_BASE, LIMIT_CLAUSE)

COUNT_SQL = '''
select count(PC.id)
    from osf_pagecounter as PC
    left join osf_guid Guid on Guid._id = split_part(PC._id, ':', 2)
    left join osf_basefilenode File on File._id = split_part(PC._id, ':', 3)
where (PC.resource_id is NULL or PC.file_id IS NULL) AND
      Guid._id IS NOT NULL AND File._id IS NOT NULL;
'''


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
            '--page_size',
            type=int,
            default=10000,
            help='How many items at a time to include for each query',
        )
        parser.add_argument(
            '--reverse',
            type=bool,
            default=False,
            help='Reverse out the migration',
        )

    # Management command handler
    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        logger.debug(options)

        dry_run = options['dry_run']
        page_size = options['page_size']
        reverse = options['reverse']
        logger.debug(
            'Dry run: {}, page size: {}, reverse: {}'.format(
                dry_run,
                page_size,
                reverse,
            )
        )

        sql_query = REVERSE_SQL_LIMITED if reverse else FORWARD_SQL_LIMITED
        logger.info('SQL Query: {}'.format(sql_query))
        with connection.cursor() as cursor:
            if not dry_run:
                cursor.execute(sql_query, [page_size])
            if not reverse:
                cursor.execute(COUNT_SQL)
                number_of_entries_left = cursor.fetchone()[0]
                logger.info('Entries left: {}'.format(number_of_entries_left))
                if number_of_entries_left == 0:
                    sentry.log_message('Migrate pagecounter data complete')

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
