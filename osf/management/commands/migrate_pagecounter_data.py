import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


REVERSE_SQL = '''
    UPDATE osf_pagecounter PC
    SET
        resource_id = NULL,
        file_id = NULL,
        version = NULL
    WHERE (pc.resource_id IS NOT NULL or pc.file_id IS NOT NULL or pc.version IS NOT NULL)
          AND PC.id >= %s AND PC.id < %s
'''

FORWARD_SQL = '''
    UPDATE osf_pagecounter PC
    SET
        action = split_part(PC._id, ':', 1),
        resource_id = Guid.id,
        file_id = File.id,
        version = NULLIF(split_part(PC._id, ':', 4), '')::int
    FROM osf_guid Guid, osf_basefilenode File
    WHERE PC.id >= %s AND PC.id < %s AND
          Guid._id = split_part(PC._id, ':', 2) AND
          File._id = split_part(PC._id, ':', 3) AND
          (PC.resource_id IS NULL or PC.file_id IS NULL or PC.version IS NULL);
'''


def get_last_record_and_count():
    with connection.cursor() as cursor:
        cursor.execute('select id from osf_pagecounter order by id desc limit 1')
        last = cursor.fetchone()[0]
        logger.debug('Last: {}'.format(last))
        cursor.execute('select count(*) from osf_pagecounter')
        count = cursor.fetchone()[0]
        logger.debug('Count: {}'.format(count))
    return last, count


class Command(BaseCommand):
    help = '''Does the work of the pagecounter migration so that it can be done incrementally when convenient.'''

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
            '--sample_only',
            type=bool,
            default=False,
            help='Only do one example of each type of detail gatherer',
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
        sample_only = options['sample_only']
        reverse = options['reverse']
        last_record, number_of_records = get_last_record_and_count()
        first_record = 1
        logger.debug(
            'Dry run: {}, page size: {}, sample only: {}, reverse: {}, last record: {}, number of records: {}'.format(
                dry_run,
                page_size,
                sample_only,
                reverse,
                last_record,
                number_of_records,
            )
        )

        sql_query = REVERSE_SQL if reverse else FORWARD_SQL
        with connection.cursor() as cursor:
            for start in range(first_record, last_record, page_size):
                end = start + page_size
                logger.info('Start of page: {}, end of page: {}, time: {}'.format(
                    start,
                    end,
                    datetime.datetime.now(),
                )
                )
                if not dry_run:
                    cursor.execute(sql_query, [start, end])
                if sample_only:
                    break
        logger.info('SQL Query: {}'.format(sql_query))

        script_finish_time = datetime.datetime.now()
        logging.info('Script finished time: {}'.format(script_finish_time))
        logging.info('Run time {}'.format(script_finish_time - script_start_time))
