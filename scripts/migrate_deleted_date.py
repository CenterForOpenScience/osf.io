import argparse
import logging

import django
from django.db import connection, transaction

from framework.celery_tasks import app as celery_app


logger = logging.getLogger(__name__)

POPULATE_COLUMNS =[
	'SET statement_timeout = 10000; UPDATE osf_comment SET deleted=modified WHERE id IN (SELECT id FROM osf_comment WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	#Assuming that the last time this comment was modified was when it was being deleted
	'SET statement_timeout = 10000; UPDATE osf_reviewaction SET deleted='epoch' WHERE id IN (SELECT id FROM osf_reviewaction WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE osf_noderequestaction SET deleted='epoch' WHERE id IN (SELECT id FROM osf_noderequestaction WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE osf_preprintrequestaction SET deleted='epoch' WHERE id IN (SELECT id FROM osf_preprintrequestaction WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	#Requests are not deleted when rejected, just a new record is created with a 'type' of reject
	'SET statement_timeout = 10000; UPDATE osf_basefilenode SET deleted = deleted_on WHERE id IN (SELECT id FROM osf_basefilenode WHERE deleted_on IS NOT NULL AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE osf_abstractnode CASE WHEN deleted_date IS NOT NULL THEN SET deleted=deleted_date ELSE SET deleted_date = last_logged END WHERE id IN (SELECT id FROM osf_abstractnode WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE osf_privatelink PL set deleted = NL.date from osf_nodelog NL, osf_privatelink_nodes pl_n WHERE NL.node_id=pl_n.abstractnode_id AND pl_n.privatelink_id = pl.id and PL.id in (SELECT id FROM osf_privatelink WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING PL.id;',

	'SET statement_timeout = 10000; UPDATE addons_zotero_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_zotero_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_dropbox_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_dropbox_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_figshare_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_figshare_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_figshare_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_figshare_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_github_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_github_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_github_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_github_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_gitlab_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_gitlab_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_gitlab_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_gitlab_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_googledrive_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_googledrive_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_googledrive_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_googledrive_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_mendeley_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_mendeley_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_mendeley_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_mendeley_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_onedrive_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_onedrive_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_onedrive_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_onedrive_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_osfstorage_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_osfstorage_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_bitbucket_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_bitbucket_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_bitbucket_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_bitbucket_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_owncloud_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_owncloud_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_owncloud_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_owncloud_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_box_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_box_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_box_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_box_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_s3_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_s3_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_dataverse_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_dataverse_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_dataverse_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_dataverse_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_s3_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_s3_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_dropbox_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_dropbox_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_twofactor_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_twofactor_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_zotero_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_zotero_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',

	'SET statement_timeout = 10000; UPDATE addons_osfstorage_usersettings SET deleted = modified WHERE id IN (SELECT id FROM addons_osfstorage_usersettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_osfstorage_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_osfstorage_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	#Not sure if this is going to change anything. I don't know if anything is ever deleted from osf_storage
	'SET statement_timeout = 10000; UPDATE addons_forward_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_forward_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;',
	'SET statement_timeout = 10000; UPDATE addons_wiki_nodesettings SET deleted = modified WHERE id IN (SELECT id FROM addons_wiki_nodesettings WHERE is_deleted AND deleted IS NULL LIMIT 1000) RETURNING id;'
]

@celery_app.task
def run_sql(sql):
	table = sql.split(' ')[5]
	logger.info('Populating deleted column in table {}'.format(table))
	with transaction.atomic():
		with connection.cursor() as cursor:
			cursor.execute(sql)
			rows = cursor.fetchall()
			if not rows:
				raise Exception('Sentry notification that {} is migrated'.format(table))

@celery_app.task(name='scripts.migrate_deleted_date')
def migrate():
    # Note:
    # To update data slowly without requiring lots of downtime,
    # add the following to CELERYBEAT_SCHEDULE in website/settings:
    #
    #   '1-minute-incremental-migrations':{
    #       'task': 'scripts.migrate_deleted_date',
    #       'schedule': crontab(minute='*/1'),
    #   },
    #
    # And let it run for about a week
    for statement in POPULATE_COLUMNS:
    	run_sql.delay(statement)

def main():
	django.setup()
	parser = argparse.ArgumentParser(
		description='Handles long-running, non-breaking db changes slowly without requiring much downtime'
	)
	parser.add_argument(
		'--dry',
		action='store_true',
		dest='dry_run',
		help='Run migration and roll back changes to db',
	)
	pargs = parser.parse_args()
	with transaction.atomic():
		if pargs.dry_run:
			raise Exception('Dry Run -- Transaction aborted.')

if __name == '__main__':
	main()





