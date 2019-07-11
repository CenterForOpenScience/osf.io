import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)

TABLES_TO_POPULATE_WITH_MODIFIED = [
    'osf_comment',
    'addons_zotero_usersettings',
    'addons_dropbox_usersettings',
    'addons_dropbox_nodesettings'
    'addons_figshare_nodesettings',
    'addons_figshare_usersettings',
    'addons_forward_nodesettings',
    'addons_github_nodesettings',
    'addons_github_usersettings',
    'addons_gitlab_nodesettings',
    'addons_gitlab_usersettings',
    'addons_googledrive_nodesettings',
    'addons_googledrive_usersettings',
    'addons_mendeley_nodesettings',
    'addons_mendeley_usersettings',
    'addons_onedrive_nodesettings',
    'addons_onedrive_usersettings',
    'addons_osfstorage_nodesettings',
    'addons_osfstorage_usersettings',
    'addons_bitbucket_nodesettings',
    'addons_bitbucket_usersettings',
    'addons_owncloud_nodesettings',
    'addons_box_nodesettings',
    'addons_owncloud_usersettings',
    'addons_box_usersettings',
    'addons_dataverse_nodesettings',
    'addons_dataverse_usersettings',
    'addons_s3_nodesettings',
    'addons_s3_usersettings',
    'addons_twofactor_usersettings',
    'addons_wiki_nodesettings',
    'addons_zotero_nodesettings'
]

TABLES_TO_POPULATE_WITH_EPOCH = [
    'osf_reviewaction',
    'osf_noderequestaction',
    'osf_preprintrequestaction'
]

POPULATE_COLUMNS = [
    'SET statement_timeout = 10000; UPDATE osf_basefilenode SET deleted = deleted_on WHERE id IN (SELECT id FROM osf_basefilenode WHERE deleted_on IS NOT NULL AND deleted IS NULL LIMIT {}) RETURNING id;',
    'SET statement_timeout = 10000; UPDATE osf_abstractnode CASE WHEN deleted_date IS NOT NULL THEN SET deleted=deleted_date ELSE SET deleted_date = last_logged END WHERE id IN (SELECT id FROM osf_abstractnode WHERE is_deleted AND deleted IS NULL LIMIT {}) RETURNING id;',
    'SET statement_timeout = 10000; UPDATE osf_privatelink PL set deleted = NL.date from osf_nodelog NL, osf_privatelink_nodes pl_n WHERE NL.node_id=pl_n.abstractnode_id AND pl_n.privatelink_id = pl.id and PL.id in (SELECT id FROM osf_privatelink WHERE is_deleted AND deleted IS NULL LIMIT {}) RETURNING PL.id;',
]

UPDATE_DELETED_WITH_MODIFIED = 'SET statement_timeout = 10000; UPDATE {} SET deleted=modified WHERE id IN (SELECT id FROM {} WHERE is_deleted AND deleted IS NULL LIMIT {}) RETURNING id;'
UPDATE_DELETED_WITH_EPOCH = 'SET statement_timeout = 10000; UPDATE {} SET deleted="epoch" WHERE id IN (SELECT id FROM {} WHERE is_deleted AND deleted IS NULL LIMIT {}) RETURNING id;',

@celery_app.task(name='management.commands.migrate_deleted_date')
def populate_deleted(dry_run=False, page_size=1000):
        for table in TABLES_TO_POPULATE_WITH_MODIFIED:
            run_statements(UPDATE_DELETED_WITH_MODIFIED, page_size, table)
        for table in TABLES_TO_POPULATE_WITH_EPOCH:
            run_statements(UPDATE_DELETED_WITH_EPOCH, page_size, table)
        for statement in POPULATE_COLUMNS:
            run_sql(statement, page_size)

def run_statements(statement, page_size, table):
    logger.info('Populating deleted column in table {}'.format(table))
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(statement.format(table, table, page_size))
            rows = cursor.fetchall()
            if not rows:
                raise Exception('Sentry notification that {} is populated'.format(table))

def run_sql(statement, page_size):
    table = statement.split(' ')[5]
    logger.info('Populating deleted column in table {}'.format(table))
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(statement.format(page_size))
            rows = cursor.fetchall()
            if not rows:
                raise Exception('Sentry notification that {} is populated'.format(table))

class Command(BaseCommand):
    help = '''Populates new deleted field for various models. Ensure you have run migrations
    before running this script.'''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry',
            type=bool,
            default=False,
            help='Run queries but do not write files',
        )
        parser.add_argument(
            '--page_size',
            type=int,
            default=1000,
            help='How many rows to process at a time',
        )

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info('Script started time: {}'.format(script_start_time))
        logger.debug(options)

        dry_run = options['dry_run']
        page_size = options['page_size']

        populate_deleted(dry_run, page_size)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
