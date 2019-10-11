import datetime
import logging

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from framework.celery_tasks import app as celery_app

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

UPDATE_DELETED_WITH_MODIFIED = """UPDATE {} SET deleted=modified
    WHERE id IN (SELECT id FROM {} WHERE is_deleted AND deleted IS NULL LIMIT {}) RETURNING id;"""

@celery_app.task(name='management.commands.addon_deleted_date')
def populate_deleted(dry_run=False, page_size=1000):
    with transaction.atomic():
        for table in TABLES_TO_POPULATE_WITH_MODIFIED:
            run_statements(UPDATE_DELETED_WITH_MODIFIED, page_size, table)
        if dry_run:
            raise RuntimeError('Dry Run -- Transaction rolled back')

def run_statements(statement, page_size, table):
    logger.info('Populating deleted column in table {}'.format(table))
    with connection.cursor() as cursor:
        cursor.execute(statement.format(table, table, page_size))
        rows = cursor.fetchall()
        if rows:
            logger.info('Table {} still has rows to populate'.format(table))

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
            default=1000,
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
