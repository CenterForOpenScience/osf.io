import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from framework.celery_tasks import app as celery_app
<<<<<<< HEAD
from framework import sentry

logger = logging.getLogger(__name__)

LIMIT_CLAUSE = ' LIMIT %s) RETURNING id;'
NO_LIMIT_CLAUSE = ');'

TABLES_TO_POPULATE_WITH_MODIFIED = [
    'osf_comment',
    'osf_institution',
    'osf_privatelink'
]

POPULATE_BASE_FILE_NODE = """UPDATE osf_basefilenode SET deleted = deleted_on
    WHERE id IN (SELECT id FROM osf_basefilenode WHERE deleted_on IS NOT NULL AND deleted IS NULL{}"""
CHECK_BASE_FILE_NODE = """SELECT deleted, deleted_on FROM osf_basefilenode WHERE deleted_on IS NOT NULL AND deleted IS NULL"""

POPULATE_ABSTRACT_NODE = """UPDATE osf_abstractnode SET deleted = CASE WHEN deleted_date IS NOT NULL THEN deleted_date ELSE last_logged END
    WHERE id IN (SELECT id FROM osf_abstractnode WHERE is_deleted AND deleted IS NULL{}"""
CHECK_ABSTRACT_NODE = """SELECT deleted, deleted_date FROM osf_abstractnode WHERE is_deleted AND deleted IS NULL"""

UPDATE_DELETED_WITH_MODIFIED = """UPDATE {} SET deleted=modified
WHERE id IN (SELECT id FROM {} WHERE is_deleted AND deleted IS NULL{}"""

CHECK_POPULATED = """SELECT deleted, is_deleted FROM {} WHERE deleted IS NULL AND is_deleted ;"""

FORWARD_BASE_FILE = POPULATE_BASE_FILE_NODE.format(NO_LIMIT_CLAUSE)
FORWARD_ABSTRACT_NODE = POPULATE_ABSTRACT_NODE.format(NO_LIMIT_CLAUSE)

REVERSE_BASE_FILE = 'UPDATE osf_basefilenode SET deleted = null'
REVERSE_ABSTRACT_NODE = 'UPDATE osf_abstractnode SET deleted = null'

FORWARD_COMMENT = UPDATE_DELETED_WITH_MODIFIED.format('osf_comment', 'osf_comment', NO_LIMIT_CLAUSE)
FORWARD_INSTITUTION = UPDATE_DELETED_WITH_MODIFIED.format('osf_institution', 'osf_institution', NO_LIMIT_CLAUSE)
FORWARD_PRIVATE_LINK = UPDATE_DELETED_WITH_MODIFIED.format('osf_privatelink', 'osf_privatelink', NO_LIMIT_CLAUSE)

REVERSE_COMMENT = 'UPDATE osf_comment SET deleted = null'
REVERSE_INSTITUTION = 'UPDATE osf_institution SET deleted = null'
REVERSE_PRIVATE_LINK = 'UPDATE osf_privatelink SET deleted = null'
=======

logger = logging.getLogger(__name__)

TABLES_TO_POPULATE_WITH_MODIFIED = [
    'addons_zotero_usersettings',
    'addons_dropbox_usersettings',
    'addons_dropbox_nodesettings',
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

POPULATE_COLUMNS = [
    'SET statement_timeout = 10000; UPDATE osf_basefilenode SET deleted = deleted_on WHERE id IN (SELECT id FROM osf_basefilenode WHERE deleted_on IS NOT NULL AND deleted IS NULL LIMIT %s) RETURNING id;',
    'SET statement_timeout = 10000; UPDATE osf_abstractnode SET deleted= CASE WHEN deleted_date IS NOT NULL THEN deleted_date ELSE last_logged END WHERE id IN (SELECT id FROM osf_abstractnode WHERE is_deleted AND deleted IS NULL LIMIT %s) RETURNING id;',
    'SET statement_timeout = 10000; UPDATE osf_privatelink PL set deleted = NL.date from osf_nodelog NL, osf_privatelink_nodes pl_n WHERE NL.node_id=pl_n.abstractnode_id AND pl_n.privatelink_id = pl.id and PL.id in (SELECT id FROM osf_privatelink WHERE is_deleted AND deleted IS NULL LIMIT %s) RETURNING PL.id;',
]

UPDATE_DELETED_WITH_MODIFIED = 'SET statement_timeout = 10000; UPDATE {} SET deleted=modified WHERE id IN (SELECT id FROM {} WHERE is_deleted AND deleted IS NULL LIMIT {}) RETURNING id;'

>>>>>>> Adding migrate script

@celery_app.task(name='management.commands.migrate_deleted_date')
def populate_deleted(dry_run=False, page_size=1000):
    with transaction.atomic():
        for table in TABLES_TO_POPULATE_WITH_MODIFIED:
            run_statements(UPDATE_DELETED_WITH_MODIFIED, page_size, table)
<<<<<<< HEAD
        run_sql(POPULATE_BASE_FILE_NODE, CHECK_BASE_FILE_NODE, page_size)
        run_sql(POPULATE_ABSTRACT_NODE, CHECK_ABSTRACT_NODE, page_size)
=======
>>>>>>> Adding migrate script
        if dry_run:
            raise RuntimeError('Dry Run -- Transaction rolled back')

def run_statements(statement, page_size, table):
    logger.info('Populating deleted column in table {}'.format(table))
    with connection.cursor() as cursor:
<<<<<<< HEAD
        cursor.execute(statement.format(table, table, LIMIT_CLAUSE), [page_size])
        rows = cursor.fetchall()
        if rows:
            cursor.execute(CHECK_POPULATED.format(table), [page_size])
            remaining_rows = cursor.fetchall()
            if not remaining_rows:
                sentry.log_message('Deleted field in {} table is populated'.format(table))

def run_sql(statement, check_statement, page_size):
    table = statement.split(' ')[1]
    logger.info('Populating deleted column in table {}'.format(table))
    with connection.cursor() as cursor:
        cursor.execute(statement.format(LIMIT_CLAUSE), [page_size])
        rows = cursor.fetchall()
        if not rows:
            with connection.cursor() as cursor:
                cursor.execute(check_statement, [page_size])
                sentry.log_message('Deleted field in {} table is populated'.format(table))
=======
        cursor.execute(statement.format(table, table, page_size))
        rows = cursor.fetchall()
        if not rows:
            logger.info('Sentry notification that {} is populated'.format(table))
>>>>>>> Adding migrate script

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
<<<<<<< HEAD
            default=10000,
=======
            default=1000,
>>>>>>> Adding migrate script
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

        populate_deleted(dry_run, page_size)

        script_finish_time = datetime.datetime.now()
        logger.info('Script finished time: {}'.format(script_finish_time))
        logger.info('Run time {}'.format(script_finish_time - script_start_time))
