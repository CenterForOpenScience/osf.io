import csv
import datetime
import logging
import requests
import tempfile

from django.core.management.base import BaseCommand
from django.db import connection
from framework.celery_tasks import app as celery_app
from requests_oauthlib import OAuth2

from website.settings import REG_METRICS_BASE_FOLDER, REG_METRICS_OSF_TOKEN

logger = logging.getLogger(__name__)

# SQL with comments provided by Courtney Soderberg

REGISTRATION_METRICS_SQL = '''
/*  calculate the number of registrations made and the number of retractions made of each type for each date that were
    made on the site during the last month, not including registrations that were canceled */

/*  get all top-level, non-deleted, registrations that were registered or retracted last month -
some approved retraction don't have retraction dates..why? */

WITH toplevel_regs AS (SELECT DISTINCT ON (osf_abstractnode.root_id) CAST(osf_abstractnode.registered_date AS DATE),
CAST(osf_retraction.date_retracted AS DATE),
        json_object_keys (registered_meta::json)
        FROM osf_abstractnode
        LEFT JOIN osf_retraction
        ON osf_abstractnode.retraction_id = osf_retraction.id
        WHERE osf_abstractnode.type = 'osf.registration'
        AND ((osf_abstractnode.registered_date >= date_trunc('month', current_date - interval '1' month)
            AND osf_abstractnode.registered_date < date_trunc('month', current_date))
            OR (osf_retraction.date_retracted >= date_trunc('month', current_date - interval '1' month)
            AND osf_retraction.date_retracted < date_trunc('month', current_date)))
            AND osf_abstractnode.is_deleted IS FALSE
        GROUP BY osf_abstractnode.root_id, CAST(osf_abstractnode.registered_date AS DATE),
            CAST(osf_retraction.date_retracted AS DATE), json_object_keys
        ORDER BY osf_abstractnode.root_id, CAST(osf_retraction.date_retracted AS DATE) ASC),
        /* count up registration events by day by form */
        reg_by_date AS (SELECT osf_registrationschema.name, toplevel_regs.registered_date AS event_date,
        COUNT(*) AS reg_events
            FROM toplevel_regs
            JOIN osf_registrationschema
            ON toplevel_regs.json_object_keys = osf_registrationschema._id
            GROUP BY osf_registrationschema.name, toplevel_regs.registered_date),
        /* count up retraction events by day by form */
        retracts_by_date AS (
            SELECT osf_registrationschema.name, toplevel_regs.date_retracted AS event_date,
            COUNT(*) AS retract_events
                FROM toplevel_regs
                JOIN osf_registrationschema
                ON toplevel_regs.json_object_keys = osf_registrationschema._id
                GROUP BY osf_registrationschema.name, toplevel_regs.date_retracted
        ),
        /* create list of all dates from last month */
        dates AS (SELECT event_date::date from generate_series(date_trunc('month', CURRENT_DATE - '1 month'::interval),
        date_trunc('month', current_date)::date -1, '1 day'::interval) event_date),
        /* crossjoin with all registration types to get a row for all combinations */
        setup AS (SELECT dates.event_date, name
            FROM dates
            CROSS JOIN (SELECT name
                            FROM osf_registrationschema
                            GROUP BY name) as schema)

/* join retraction and registrations onto crossjoin so that we have an entry for each registration form for each date */

SELECT setup.event_date, setup.name, coalesce(reg_events, 0)
AS reg_events, coalesce(retract_events,0) AS retract_events,
coalesce(reg_events, 0) - coalesce(retract_events,0) AS net_events
    FROM setup
    LEFT JOIN reg_by_date
    ON setup.event_date = reg_by_date.event_date AND setup.name = reg_by_date.name
    LEFT JOIN retracts_by_date
    ON setup.event_date = retracts_by_date.event_date AND setup.name = retracts_by_date.name;
'''
TEMP_FOLDER = tempfile.mkdtemp(suffix='/')
VALUES = (
    'event_date',
    'name',
    'reg_events',
    'retract_events',
    'net_events',
)

def bearer_token_auth(token):
    token_dict = {
        'token_type': 'Bearer',
        'access_token': token
    }
    return OAuth2(token=token_dict)


def upload_to_storage(file_path, upload_url, params):
    logger.debug('Uploading {} to {}'.format(file_path, upload_url))
    with open(file_path, 'r') as summary_file:
        requests.put(
            url=upload_url,
            params=params,
            data=summary_file,
            auth=bearer_token_auth(REG_METRICS_OSF_TOKEN),
        )


def encode_row(row):
    row_to_write = []
    for s in row:
        item = s.encode('utf-8') if isinstance(s, str) else s
        row_to_write.append(item)
    return row_to_write


def write_raw_data(cursor, filename):
    file_path = '{}{}'.format(TEMP_FOLDER, filename)
    params = {
        'kind': 'file',
        'name': filename,
    }
    logger.debug('Writing to {}'.format(file_path))
    with open(file_path, 'w') as new_file:
        writer = csv.writer(new_file, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
        writer.writerow(list(VALUES))
        for row in cursor.fetchall():
            writer.writerow(row)
    upload_to_storage(file_path=file_path, upload_url=REG_METRICS_BASE_FOLDER, params=params)


@celery_app.task(name='management.commands.registration_schema_metrics')
def gather_metrics(dry_run=False):
    today = datetime.date.today()
    first = today.replace(day=1)
    last_month = first - datetime.timedelta(days=1)
    filename = 'form_types_{}.csv'.format(last_month.strftime('%Y-%m'))

    with connection.cursor() as cursor:
        cursor.execute(REGISTRATION_METRICS_SQL)
        if dry_run:
            for row in cursor.fetchall():
                logger.info(encode_row(row))
        else:
            write_raw_data(cursor=cursor, filename=filename)


class Command(BaseCommand):
    help = '''Counts the number of registrations made and retracted in the past month, grouped by provider'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not write files',
        )

    # Management command handler
    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        logger.debug(options)

        dry_run = options['dry_run']

        if dry_run:
            logger.info('DRY RUN')

        gather_metrics(dry_run=dry_run)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
