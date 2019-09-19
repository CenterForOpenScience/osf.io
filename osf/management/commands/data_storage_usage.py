# -*- coding: utf-8 -*-
import csv
import datetime
import logging
import requests
import tempfile
import zipfile

from collections import OrderedDict
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import connection
from requests_oauthlib import OAuth2

try:
    from StringIO import StringIO  # Python2
except ImportError:
    from io import StringIO  # Python 3

from framework import sentry
from framework.celery_tasks import app as celery_app
from website.settings import DS_METRICS_BASE_FOLDER, DS_METRICS_OSF_TOKEN

DEFAULT_API_VERSION = '2.14'
TEMP_FOLDER = tempfile.mkdtemp(suffix='/')
VALUES = [
    'file_version_id',
    'file_id',
    'version_id',
    'target_object',
    'target_content_type_id',
    'deleted_on',
    'size',
    'region',
    'target_guid',
    'target_title',
    'target_type',
    'target_is_public',
    'target_is_fork',
    'target_root',
    'target_is_deleted',
    'target_spam_status',
    'target_is_supplementary_node'
]

# Grab the id of end of the basefilenode_version table for query limiting
LAST_ROW_SQL = """
    SELECT
        obfnv.id AS fileversion_id
    FROM osf_basefileversionsthrough AS obfnv
    ORDER BY obfnv.id DESC
    LIMIT 1
"""

# Get the raw data for all of the node-based items
NODE_LIST_SQL = """
        SELECT
           obfnv.id AS basefileversion_id,
           obfnv.basefilenode_id,
           obfnv.fileversion_id,
           file.target_object_id,
           file.target_content_type_id,
           file.deleted_on,
           version.size,
           region.name AS region,
           guid._id AS guid,
           node.title AS node_title,
           node.type AS node_type,
           node.is_public,
           node.is_fork,
           root_guid._id AS root_guid,
           node.is_deleted AS node_deleted,
           node.spam_status,
           preprint.id IS NOT NULL AS is_supplementary_node
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN addons_osfstorage_region region ON version.region_id = region.id
        LEFT JOIN osf_abstractnode node ON node.id = file.target_object_id
        LEFT JOIN osf_preprint preprint ON preprint.node_id = node.id
        LEFT JOIN osf_guid guid ON (node.id = guid.object_id AND guid.content_type_id = %s)
        LEFT JOIN osf_guid root_guid ON (node.root_id = root_guid.object_id AND root_guid.content_type_id = %s)
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
        AND obfnv.id >= %s AND obfnv.id <= %s
    """

# Aggregation of total file size based on the node query above
TOTAL_FILE_SIZE_SUM_SQL = """
    SELECT
       'total', sum(size) AS deleted_size_sum
    FROM osf_basefileversionsthrough AS obfnv
    LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
    LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
    WHERE file.provider = 'osfstorage'
      AND obfnv.id >= %s AND obfnv.id <= %s
    """

# Aggregation of deleted files based on the node query above
DELETED_FILE_SIZE_SUM_SQL = """
    SELECT
       'deleted', sum(size) AS deleted_size_sum
    FROM osf_basefileversionsthrough AS obfnv
    LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
    LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
    WHERE file.provider = 'osfstorage'
      AND file.deleted_on IS NOT NULL
      AND obfnv.id >= %s AND obfnv.id <= %s
    """

#  Aggregation of the regional node file content based on the node query above
REGIONAL_NODE_SIZE_SUM_SQL = """
        SELECT
           region.name, sum(size)
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN addons_osfstorage_region region ON version.region_id = region.id
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
        AND obfnv.id >= %s AND obfnv.id <= %s
        GROUP BY region.name
    """

# Aggregation of files in registries and non-deleted, public nodes based on the node query above
ABSTRACT_NODE_SIZE_SUM_SQL = """
        SELECT
           CASE WHEN (
               node.type = 'osf.node' AND NOT node.is_public
           ) THEN 'osf.private-node' ELSE node.type END AS type,
           sum(size)
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN osf_abstractnode node ON file.target_object_id = node.id
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
          AND (node.type = 'osf.registration' or node.type = 'osf.node')
          AND node.is_deleted = False
          AND file.deleted_on IS NULL
          AND obfnv.id >= %s AND obfnv.id <= %s
        GROUP BY node.type, node.is_public
    """

# Aggregation of non-deleted quick file sizes (NOTE: This will break when QuickFolders is merged)
ND_QUICK_FILE_SIZE_SUM_SQL = """
        SELECT
           node.type, sum(size)
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN osf_abstractnode node ON file.target_object_id = node.id
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
          AND node.type = 'osf.quickfilesnode'
          AND node.is_deleted = False
          AND file.deleted_on IS NULL
          AND obfnv.id >= %s AND obfnv.id <= %s
        GROUP BY node.type

    """

# Aggregation of size of non-deleted files in preprint supplemental nodes based on the node query above
ND_PREPRINT_SUPPLEMENT_SIZE_SUM_SQL = """
        SELECT
           'nd_supplement', sum(size) AS supplementary_node_size
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN osf_abstractnode node ON node.id = file.target_object_id
        LEFT JOIN osf_preprint preprint ON preprint.node_id = node.id
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
          AND preprint.id IS NOT NULL AND preprint.deleted IS NULL
          AND node.is_deleted = False
          AND file.deleted_on IS NULL
          AND obfnv.id >= %s AND obfnv.id <= %s
    """

# Raw data for preprints
PREPRINT_LIST_SQL = """
        SELECT
           obfnv.id AS basefileversion_id,
           basefilenode_id,
           fileversion_id,
           file.target_object_id,
           file.target_content_type_id,
           file.deleted_on,
           version.size,
           region.name AS region,
           guid._id AS preprint_guid,
           preprint.title AS preprint_title,
           'osf.preprint' AS type,
           preprint.is_public,
           FALSE AS is_fork,
           guid._id AS root_guid,
           preprint.deleted IS NOT NULL AS preprint_deleted,
           preprint.spam_status,
           FALSE AS is_supplementary_node
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN addons_osfstorage_region region ON version.region_id = region.id
        LEFT JOIN osf_preprint preprint ON preprint.id = file.target_object_id
        LEFT JOIN osf_guid guid ON (preprint.id = guid.object_id AND guid.content_type_id = %s)
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
          AND obfnv.id >= %s AND obfnv.id <= %s
    """

# Aggregation of non-deleted preprint file sizes (not including supplementary files)
ND_PREPRINT_SIZE_SUM_SQL = """
        SELECT
           'nd_preprints', sum(size) AS nd_preprint_size_sum
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN osf_preprint preprint ON preprint.id = file.target_object_id
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
          AND preprint.deleted IS NULL AND file.deleted_on IS NULL
          AND obfnv.id >= %s AND obfnv.id <= %s
    """

# Aggregation of preprint file sizes grouped by region
REGIONAL_PREPRINT_SIZE_SUM_SQL = """
        SELECT
           region.name, sum(size)
        FROM osf_basefileversionsthrough AS obfnv
        LEFT JOIN osf_basefilenode file ON obfnv.basefilenode_id = file.id
        LEFT JOIN osf_fileversion version ON obfnv.fileversion_id = version.id
        LEFT JOIN addons_osfstorage_region region ON version.region_id = region.id
        WHERE file.provider = 'osfstorage' AND file.target_content_type_id = %s
          AND obfnv.id >= %s AND obfnv.id <= %s
        GROUP BY region.name
    """

logger = logging.getLogger(__name__)


# 1. Get content types for nodes, registration, preprints,
def get_content_types(cursor):
    sql = """
        SELECT concat(app_label, '.', model) AS type, id
        FROM django_content_type type
        WHERE type.model IN (
                             'abstractnode',
                             'preprint'
                            )
    """
    cursor.execute(sql)
    return {key: value for key, value in cursor.fetchall()}


def convert_value(value):
    if value == 'None' or value is None:
        return 0
    if isinstance(value, Decimal):
        return int(value)
    return value


def combine_summary_data(*args):
    combined_summary_data = {}
    for summary_data_item in args:
        logger.debug(summary_data_item)
        if isinstance(summary_data_item, dict):
            for key in summary_data_item.keys():
                combined_summary_data[key] = combined_summary_data.get(key, 0) + convert_value(
                    summary_data_item.get(key, 0)
                )
        elif isinstance(summary_data_item, list):
            for key, value in summary_data_item:
                combined_summary_data[key] = combined_summary_data.get(key, 0) + convert_value(value)
    return combined_summary_data


def summarize(sql, content_type, start, end, cursor):
    cursor.execute(
        sql,
        [
            content_type,
            start,
            end,
        ]
    )
    return cursor.fetchall()


def gather_usage_data(start, end, dry_run, zip_file):
    logger.info('Start: {}, end: {}, dry run: {}'.format(start, end, dry_run))
    with connection.cursor() as cursor:
        content_types = get_content_types(cursor)
        abstractnode_content_type = content_types['osf.abstractnode']
        preprint_content_type = content_types['osf.preprint']

        logger.debug('Gathering node usage at {}'.format(datetime.datetime.now()))
        filename = './data-usage-raw-nodes-{}-{}.csv'.format(start, end)
        cursor.execute(
            NODE_LIST_SQL,
            [
                abstractnode_content_type,
                abstractnode_content_type,
                abstractnode_content_type,
                start,
                end,
            ]
        )
        if not dry_run:
            logger.debug('Writing {} to zip'.format(filename))
            write_raw_data(cursor=cursor, zip_file=zip_file, filename=filename)

        logger.debug('Gathering abstractnode summary at {}'.format(datetime.datetime.now()))
        summary_data = combine_summary_data(summarize(
            sql=ABSTRACT_NODE_SIZE_SUM_SQL,
            content_type=abstractnode_content_type,
            start=start,
            end=end,
            cursor=cursor,
        ))
        logger.debug('Gathering regional node summary at {}'.format(datetime.datetime.now()))
        summary_data = combine_summary_data(summary_data, summarize(
            sql=REGIONAL_NODE_SIZE_SUM_SQL,
            content_type=abstractnode_content_type,
            start=start,
            end=end,
            cursor=cursor,
        ))

        # TODO: Move the next when Quick Folders is done
        logger.debug('Gathering quickfile summary at {}'.format(datetime.datetime.now()))
        summary_data = combine_summary_data(summary_data, summarize(
            sql=ND_QUICK_FILE_SIZE_SUM_SQL,
            content_type=abstractnode_content_type,
            start=start,
            end=end,
            cursor=cursor,
        ))

        logger.debug('Gathering supplement summary at {}'.format(datetime.datetime.now()))
        summary_data = combine_summary_data(summary_data, summarize(
            sql=ND_PREPRINT_SUPPLEMENT_SIZE_SUM_SQL,
            content_type=abstractnode_content_type,
            start=start,
            end=end,
            cursor=cursor,
        ))
        logger.debug('Gathering deleted file summary at {}'.format(datetime.datetime.now()))
        cursor.execute(
            DELETED_FILE_SIZE_SUM_SQL,
            [
                start,
                end,
            ]
        )
        summary_data = combine_summary_data(summary_data, cursor.fetchall())
        logger.debug('Gathering total file summary at {}'.format(datetime.datetime.now()))
        cursor.execute(
            TOTAL_FILE_SIZE_SUM_SQL,
            [
                start,
                end,
            ]
        )
        summary_data = combine_summary_data(summary_data, cursor.fetchall())

        logger.debug('Gathering preprint usage at {}'.format(datetime.datetime.now()))
        filename = './data-usage-raw-preprints-{}-{}.csv'.format(start, end)

        cursor.execute(
            PREPRINT_LIST_SQL,
            [
                preprint_content_type,
                preprint_content_type,
                start,
                end,
            ]
        )
        if not dry_run:
            logger.debug('Writing {} to zip.'.format(filename))
            write_raw_data(cursor=cursor, zip_file=zip_file, filename=filename)

        logger.debug('Gathering preprint summary at {}'.format(datetime.datetime.now()))
        summary_data = combine_summary_data(summary_data, summarize(
            sql=ND_PREPRINT_SIZE_SUM_SQL,
            content_type=preprint_content_type,
            start=start,
            end=end,
            cursor=cursor,
        ))
        logger.debug('Gathering regional preprint summary at {}'.format(datetime.datetime.now()))
        summary_data = combine_summary_data(summary_data, summarize(
            sql=REGIONAL_PREPRINT_SIZE_SUM_SQL,
            content_type=preprint_content_type,
            start=start,
            end=end,
            cursor=cursor,
        ))

    return summary_data


def write_summary_data(filename, summary_data, remote_base_folder):
    header_row = summary_data.keys()
    summary_row = summary_data.values()
    file_path = '{}{}'.format(TEMP_FOLDER, filename)
    old_remote = requests.get(
        url=remote_base_folder['files'],
        headers={'Accept': 'application/vnd.api+json;version={}'.format(DEFAULT_API_VERSION)},
        auth=bearer_token_auth(DS_METRICS_OSF_TOKEN),
        params={'filter[name]': filename},
    ).json()
    try:
        logger.debug('json: {}'.format(old_remote))
        if old_remote[u'meta'][u'total'] > 1:
            sentry.log_message(
                'Too many files that look like {} - this may cause problems for data storage usage summaries'.format(
                    remote_base_folder['files']
                )
            )
        old_remote_data = old_remote['data'][0]
        upload = old_remote_data['links']['upload']
        params = {'kind': 'file'}

        header_skipped = False
        with open(file_path, 'w') as new_file:
            writer = csv.writer(new_file, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
            writer.writerow(header_row)
            with requests.get(
                    url=upload,  # Yes, upload is correct here.
                    headers={'Accept': 'application/vnd.api+json;version={}'.format(DEFAULT_API_VERSION)},
                    auth=bearer_token_auth(DS_METRICS_OSF_TOKEN),
                    stream=True,
            ) as old_file:
                reader = csv.reader(old_file.iter_lines(), delimiter=',', lineterminator='\n')
                for row in reader:
                    if header_skipped:
                        writer.writerow(row)
                    header_skipped = True
            writer.writerow(summary_row)

    except IndexError:
        upload = remote_base_folder['upload']
        params = {
            'kind': 'file',
            'name': filename,
        }
        with open(file_path, 'w') as new_file:
            writer = csv.writer(new_file, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
            writer.writerow(header_row)
            writer.writerow(summary_row)

    upload_to_storage(file_path=file_path, upload_url=upload, params=params)


def write_raw_data(cursor, zip_file, filename):
    data_buffer = StringIO()
    writer = csv.writer(data_buffer, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
    writer.writerow(VALUES)
    for row in cursor.fetchall():
        row_to_write = []
        for s in row:
            item = s.encode('utf-8') if isinstance(s, (str, unicode)) else s
            row_to_write.append(item)
        writer.writerow(row_to_write)
    zip_file.writestr(filename, data_buffer.getvalue())


def upload_to_storage(file_path, upload_url, params):
    logger.debug('Uploading {} to {}'.format(file_path, upload_url))
    with open(file_path, 'r') as summary_file:
        requests.put(
            url=upload_url,
            headers={'Accept': 'application/vnd.api+json;version={}'.format(DEFAULT_API_VERSION)},
            params=params,
            data=summary_file,
            auth=bearer_token_auth(DS_METRICS_OSF_TOKEN),
        )


@celery_app.task(name='management.commands.data_storage_usage')
def process_usages(
        dry_run=False,
        page_size=10000,
        sample_only=False,
):
    if not dry_run:
        json = requests.get(
            url=DS_METRICS_BASE_FOLDER,
            headers={'Accept': 'application/vnd.api+json;version={}'.format(DEFAULT_API_VERSION)},
            auth=bearer_token_auth(DS_METRICS_OSF_TOKEN)
        ).json()['data']

        remote_base_folder = {
            'files': json['relationships']['files']['links']['related']['href'],
            'new_folder': json['links']['new_folder'],
            'upload': json['links']['upload'],
        }
        logger.debug('Remote base folder: {}'.format(remote_base_folder))
    # We can't re-order these columns after they are released, only add columns to the end
    # This is why we can't just append whatever storage regions we add to the system automatically,
    # because then they'd likely be out of order when they were added.

    logger.debug('Getting last item - {}'.format(datetime.datetime.now()))
    with connection.cursor() as cursor:
        cursor.execute(LAST_ROW_SQL)
        last_item = cursor.fetchone()[0]
    logger.debug('Last item: {}'.format(last_item))
    summary_data = OrderedDict([
        ('date', date.today().isoformat()),
        ('total', 0),
        ('deleted', 0),
        ('registrations', 0),
        ('nd_quick_files', 0),
        ('nd_public_nodes', 0),
        ('nd_private_nodes', 0),
        ('nd_preprints', 0),
        ('nd_supp_nodes', 0),
        ('canada_montreal', 0),
        ('australia_sydney', 0),
        ('germany_frankfurt', 0),
        ('united_states', 0),
    ])
    logger.debug('Collecting usage details - {}'.format(datetime.datetime.now()))
    summary_totals = {}
    start = 0
    end = min(page_size, last_item)
    keep_going = True
    now = datetime.datetime.now()
    zip_file_name = 'data_storage_raw_{}.zip'.format(now)
    zip_file_path = '{}{}'.format(TEMP_FOLDER, zip_file_name)
    with zipfile.ZipFile(
            zip_file_path, mode='w', compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        while keep_going:
            summary_totals = combine_summary_data(
                summary_totals,
                gather_usage_data(
                    start=start,
                    end=end,
                    dry_run=dry_run,
                    zip_file=zip_file,
                )
            )
            start = end + 1
            end = min(end + page_size, last_item)
            keep_going = (start <= end) and (not sample_only)
    logger.debug(summary_totals)

    if not dry_run:
        upload_to_storage(
            file_path=zip_file_path,
            upload_url=remote_base_folder['upload'],
            params={
                'kind': 'file',
                'name': zip_file_name,
            }
        )

    summary_data['total'] = summary_totals.get('total', 0)
    summary_data['deleted'] = summary_totals.get('deleted', 0)
    summary_data['registrations'] = summary_totals.get('osf.registration', 0)
    summary_data['nd_quick_files'] = summary_totals.get('osf.quickfilesnode', 0)
    summary_data['nd_public_nodes'] = summary_totals.get('osf.node', 0)
    summary_data['nd_private_nodes'] = summary_totals.get('osf.private-node', 0)
    summary_data['nd_preprints'] = summary_totals.get('nd_preprints', 0)
    summary_data['nd_supp_nodes'] = summary_totals.get('nd_supplement', 0)
    summary_data['canada_montreal'] = summary_totals.get(u'Canada - Montréal', 0)
    summary_data['australia_sydney'] = summary_totals.get('Australia - Sydney', 0)
    summary_data['germany_frankfurt'] = summary_totals.get('Germany - Frankfurt', 0)
    summary_data['united_states'] = summary_totals.get('United States', 0)
    if not dry_run:
        write_summary_data(
            filename='osf_storage_metrics.csv',
            summary_data=summary_data,
            remote_base_folder=remote_base_folder
        )

    return summary_data


def bearer_token_auth(token):
    token_dict = {
        'token_type': 'Bearer',
        'access_token': token
    }
    return OAuth2(token=token_dict)


class Command(BaseCommand):
    help = '''Get raw and summary data of storage usage for Product and Metascience.
    For remote upload, add a setting for DS_METRICS_API_TOKEN that has write access to a waterbutler info URL
    for a folder on an OSF project stored in the DS_METRICS_BASE_FOLDER setting. WARNING: If you are making
    changes to this and are using Production data, do not put the data that this script outputs anywhere that
    you wouldn't put production data.'''

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

    # Management command handler
    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        logger.debug(options)

        dry_run = options['dry_run']
        page_size = options['page_size']
        sample_only = options['sample_only']

        if dry_run:
            logger.info('DRY RUN')
        else:
            if DS_METRICS_BASE_FOLDER is None or DS_METRICS_OSF_TOKEN is None:
                raise RuntimeError(
                    'DS_METRICS_BASE_FOLDER and DS_METRICS_OSF_TOKEN settings are required if dry_run==False.'
                )

        logger.debug('Dry run: {}, page size: {}, sample only: {}, temp folder: {}'.format(
            dry_run,
            page_size,
            sample_only,
            TEMP_FOLDER
        ))
        process_usages(
            dry_run=dry_run,
            page_size=page_size,
            sample_only=sample_only,
        )
        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
