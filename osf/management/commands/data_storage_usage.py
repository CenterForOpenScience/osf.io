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

from website.settings import DS_METRICS_BASE_FOLDER, DS_METRICS_OSF_TOKEN

DEFAULT_API_VERSION = '2.14'
TEMP_FOLDER = tempfile.mkdtemp(suffix='/')
VALUES = (
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
)
LAST_ROW_SQL = """
    select
        obfnv.id as fileversion_id
    from osf_basefilenode_versions as obfnv
    order by obfnv.id DESC
    LIMIT 1
"""
NODE_LIST_SQL = """
        select
           obfnv.id as basefileversion_id,
           obfnv.basefilenode_id,
           obfnv.fileversion_id,
           file.target_object_id,
           file.target_content_type_id,
           file.deleted_on,
           version.size,
           region.name as region,
           guid._id as guid,
           node.title as node_title,
           node.type as node_type,
           node.is_public,
           node.is_fork,
           root_guid._id as root_guid,
           node.is_deleted as node_deleted,
           node.spam_status,
           preprint.id is not null as is_supplementary_node
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left outer join osf_fileversion version on obfnv.fileversion_id = version.id
        left outer join addons_osfstorage_region region on version.region_id = region.id
        left outer join osf_abstractnode node on node.id = file.target_object_id
        left outer join osf_preprint preprint on preprint.node_id = node.id
        LEFT outer JOIN osf_guid guid ON (node.id = guid.object_id AND guid.content_type_id = %s)
        left outer join osf_guid root_guid ON (node.id = root_guid.object_id AND root_guid.content_type_id = %s)
        where file.provider = 'osfstorage' and file.target_content_type_id = %s
        and obfnv.id >= %s and obfnv.id <= %s
        order by obfnv.id
    """
TOTAL_FILE_SIZE_SUM_SQL = """
    select
       'total', sum(size) as deleted_size_sum
    from osf_basefilenode_versions as obfnv
    left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
    left outer join osf_fileversion version on obfnv.fileversion_id = version.id
    where file.provider = 'osfstorage'
      and obfnv.id > %s and obfnv.id <= %s
    """
DELETED_FILE_SIZE_SUM_SQL = """
    select
       'deleted', sum(size) as deleted_size_sum
    from osf_basefilenode_versions as obfnv
    left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
    left outer join osf_fileversion version on obfnv.fileversion_id = version.id
    where file.provider = 'osfstorage'
      and file.deleted_on is not null
      and obfnv.id > %s and obfnv.id <= %s
    """
REGIONAL_NODE_SIZE_SUM_SQL = """
        select
           region.name, sum(size)
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left join osf_fileversion version on obfnv.fileversion_id = version.id
        left join addons_osfstorage_region region on version.region_id = region.id
        where file.provider = 'osfstorage' and file.target_content_type_id = %s
        and obfnv.id >= %s and obfnv.id <= %s
        group by region.name
    """
ABSTRACT_NODE_SIZE_SUM_SQL = """
        select
           node.type, sum(size)
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left outer join osf_fileversion version on obfnv.fileversion_id = version.id
        left outer join addons_osfstorage_region region on version.region_id = region.id
        left outer join osf_abstractnode node on file.target_object_id = node.id
        where file.provider = 'osfstorage' and file.target_content_type_id = %s
          and (node.type != 'osf.node' or (node.type = 'osf.node' and node.is_public = TRUE))
          and node.type != 'osf.quickfilesnode'
          and node.is_deleted = False
          and file.deleted_on is Null
          and obfnv.id >= %s and obfnv.id <= %s
        group by node.type
    """
ND_QUICK_FILE_SIZE_SUM_SQL = """
        select
           node.type, sum(size)
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left outer join osf_fileversion version on obfnv.fileversion_id = version.id
        left outer join addons_osfstorage_region region on version.region_id = region.id
        left outer join osf_abstractnode node on file.target_object_id = node.id
        where file.provider = 'osfstorage' and file.target_content_type_id = %s
          and node.type = 'osf.quickfilesnode'
          and file.deleted_on is null
          and obfnv.id >= %s and obfnv.id <= %s
        group by node.type

    """
ND_PREPRINT_SUPPLEMENT_SIZE_SUM_SQL = """
        select
           'nd_supplement', sum(size) as supplementary_node_size
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left outer join osf_fileversion version on obfnv.fileversion_id = version.id
        left outer join osf_abstractnode node on node.id = file.target_object_id
        left outer join osf_preprint preprint on preprint.node_id = node.id
        where file.provider = 'osfstorage' and file.target_content_type_id = %s
          and preprint.id is not null and preprint.deleted is null
          and file.deleted_on is null
          and obfnv.id > %s and obfnv.id <= %s
    """
PREPRINT_LIST_SQL = """
        select
           obfnv.id as basefileversion_id,
           basefilenode_id,
           fileversion_id,
           file.target_object_id,
           file.target_content_type_id,
           file.deleted_on,
           version.size,
           region.name as region,
           guid._id as preprint_guid,
           preprint.title as preprint_title,
           'osf.preprint' as type,
           preprint.is_public,
           FALSE as is_fork,
           guid._id as root_guid,
           preprint.deleted is not null as preprint_deleted,
           preprint.spam_status,
           FALSE as is_supplementary_node
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left outer join osf_fileversion version on obfnv.fileversion_id = version.id
        left outer join addons_osfstorage_region region on version.region_id = region.id
        left outer join osf_preprint preprint on preprint.id = file.target_object_id
        LEFT OUTER JOIN osf_guid guid ON (preprint.id = guid.object_id AND guid.content_type_id = %s)
        where file.provider like 'osfstorage' and file.target_content_type_id = %s
          and obfnv.id >= %s and obfnv.id <= %s
    """
ND_PREPRINT_SIZE_SUM_SQL = """
        select
           'nd_preprints', sum(size) as nd_preprint_size_sum
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left join osf_fileversion version on obfnv.fileversion_id = version.id
        left join addons_osfstorage_region region on version.region_id = region.id
        left join osf_preprint preprint on preprint.id = file.target_object_id
        where file.provider like 'osfstorage' and file.target_content_type_id = %s
          and preprint.deleted is null and file.deleted_on is null
          and obfnv.id > %s and obfnv.id <= %s
    """
REGIONAL_PREPRINT_SIZE_SUM_SQL = """
        select
           region.name, sum(size)
        from osf_basefilenode_versions as obfnv
        left outer join osf_basefilenode file on obfnv.basefilenode_id = file.id
        left join osf_fileversion version on obfnv.fileversion_id = version.id
        left join addons_osfstorage_region region on version.region_id = region.id
        left join osf_preprint preprint on preprint.id = file.target_object_id
        where file.provider like 'osfstorage' and file.target_content_type_id = %s
          and obfnv.id > %s and obfnv.id <= %s
        group by region.name
    """

logger = logging.getLogger(__name__)


# 1. Get content types for nodes, registration, preprints,
def get_content_types(cursor):
    sql = """
        select concat(app_label, '.', model) as type, id
        from django_content_type type
        where type.model in (
                             'abstractnode',
                             'node',
                             'preprint',
                             'quickfilesnode'
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

        logger.info('Gathering node usage at {}'.format(datetime.datetime.now()))
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
            logger.info('Writing {} to zip'.format(filename))
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
            logger.info('Writing {} to zip.'.format(filename))
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
    header_row = []
    summary_row = []
    for key in summary_data:
        header_row += [key]
        summary_row += [summary_data[key]]
    file_path = '{}{}'.format(TEMP_FOLDER, filename)
    old_remote = requests.get(
        url=remote_base_folder['files'],
        auth=bearer_token_auth(DS_METRICS_OSF_TOKEN),
        params={'filter[name]': filename},
    ).json()
    try:
        old_remote_data = old_remote['data'][0]
        upload = old_remote_data['links']['upload']
        params = {'kind': 'file'}
        old_file_path = old_remote_data['links']['upload']  # Yes, upload is correct here.

        header_skipped = False
        with open(file_path, 'w') as new_file:
            writer = csv.writer(new_file, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL)
            writer.writerow(header_row)
            with requests.get(
                    url=old_file_path,
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
    writer.writerow(list(VALUES))
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
            params=params,
            data=summary_file,
            auth=bearer_token_auth(DS_METRICS_OSF_TOKEN),
        )


def process_usages(
        dry_run=False,
        page_size=10000,
        sample_only=False,
        remote_base_folder=None,
):
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
        ('nd_preprints', 0),
        ('nd_supp_nodes', 0),
        ('canada_montreal', 0),
        ('australia_syndey', 0),
        ('germany_frankfurt', 0),
        ('united_states', 0),
    ])
    logger.info('Collecting usage details - {}'.format(datetime.datetime.now()))
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
    summary_data['nd_preprints'] = summary_totals.get('nd_preprints', 0)
    summary_data['nd_supp_nodes'] = summary_totals.get('nd_supplement', 0)
    summary_data['canada_montreal'] = summary_totals.get(u'Canada - Montréal', 0)
    summary_data['australia_syndey'] = summary_totals.get('Australia - Sydney', 0)
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
    for a folder on an OSF project stored in the DS_METRICS_BASE_FOLDER setting.'''

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
        logging.info('Script started time: {}'.format(script_start_time))
        logging.debug(options)

        dry_run = options['dry_run']
        page_size = options['page_size']
        sample_only = options['sample_only']

        remote_base_folder = None

        if not dry_run:
            if DS_METRICS_BASE_FOLDER is not None and DS_METRICS_OSF_TOKEN is not None:
                json = requests.get(
                    url=DS_METRICS_BASE_FOLDER,
                    headers={'Accept-Header': 'application/vnd.api+json;version={}'.format(DEFAULT_API_VERSION)},
                    auth=bearer_token_auth(DS_METRICS_OSF_TOKEN)
                ).json()['data']

                remote_base_folder = {
                    'files': json['relationships']['files']['links']['related']['href'],
                    'new_folder': json['links']['new_folder'],
                    'upload': json['links']['upload'],
                }
            else:
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
            remote_base_folder=remote_base_folder,
        )
        script_finish_time = datetime.datetime.now()
        logging.info('Script finished time: {}'.format(script_finish_time))
        logging.info('Run time {}'.format(script_finish_time - script_start_time))
