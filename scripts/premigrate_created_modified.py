import argparse
import logging

import django
from django.db import connection, transaction

from framework.celery_tasks import app as celery_app


logger = logging.getLogger(__name__)

ADD_COLUMNS = [
    'ALTER TABLE osf_basefilenode ADD COLUMN created timestamp with time zone;',
    'ALTER TABLE osf_basefilenode ADD COLUMN modified timestamp with time zone;',
    "ALTER TABLE osf_blacklistguid ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_blacklistguid ADD COLUMN modified timestamp with time zone;",
    'ALTER TABLE osf_fileversion ADD COLUMN created timestamp with time zone;',
    'ALTER TABLE osf_fileversion ADD COLUMN modified timestamp with time zone;',
    "ALTER TABLE osf_guid ADD COLUMN modified timestamp with time zone;",
    'ALTER TABLE osf_nodelog ADD COLUMN created timestamp with time zone;',
    'ALTER TABLE osf_nodelog ADD COLUMN modified timestamp with time zone;',
    "ALTER TABLE osf_pagecounter ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_pagecounter ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_abstractnode ADD COLUMN last_logged timestamp with time zone;",
    "ALTER TABLE osf_institution ADD COLUMN last_logged timestamp with time zone;",
]

POPULATE_COLUMNS = [
    "SET statement_timeout = 10000; UPDATE osf_basefilenode SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch' WHERE id IN (SELECT id FROM osf_basefilenode WHERE created IS NULL LIMIT 1000) RETURNING id;",
    "SET statement_timeout = 10000; UPDATE osf_blacklistguid SET created='epoch', modified='epoch' WHERE id IN (SELECT id FROM osf_blacklistguid WHERE created IS NULL LIMIT 1000) RETURNING id;",
    "SET statement_timeout = 10000; UPDATE osf_fileversion SET created=date_created, modified='epoch' WHERE id IN (SELECT id FROM osf_fileversion WHERE created IS NULL LIMIT 1000) RETURNING id;",
    "SET statement_timeout = 10000; UPDATE osf_guid SET modified='epoch' WHERE id IN (SELECT id FROM osf_guid WHERE modified IS NULL LIMIT 1000) RETURNING id;",
    "SET statement_timeout = 10000; UPDATE osf_nodelog SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch' WHERE id IN (SELECT id FROM osf_nodelog WHERE created IS NULL LIMIT 1000) RETURNING id;",
    "SET statement_timeout = 10000; UPDATE osf_pagecounter SET created='epoch', modified='epoch' WHERE id IN (SELECT id FROM osf_pagecounter WHERE created IS NULL LIMIT 1000) RETURNING id;",
]

FINALIZE_MIGRATION = [
    "UPDATE osf_basefilenode SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch' WHERE created IS NULL;",
    'ALTER TABLE osf_basefilenode ALTER COLUMN created SET NOT NULL;',
    'ALTER TABLE osf_basefilenode ALTER COLUMN modified SET NOT NULL;',
    "UPDATE osf_blacklistguid SET created='epoch', modified='epoch' WHERE created IS NULL;",
    "ALTER TABLE osf_blacklistguid ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_blacklistguid ALTER COLUMN modified SET NOT NULL;",
    "UPDATE osf_fileversion SET created=date_created, modified='epoch' WHERE created IS NULL;",
    'ALTER TABLE osf_fileversion ALTER COLUMN created SET NOT NULL;',
    'ALTER TABLE osf_fileversion ALTER COLUMN modified SET NOT NULL;',
    'ALTER TABLE osf_fileversion DROP COLUMN date_created;',
    "UPDATE osf_guid SET modified='epoch' WHERE modified IS NULL;",
    "ALTER TABLE osf_guid ALTER COLUMN modified SET NOT NULL;",
    "UPDATE osf_nodelog SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch' WHERE created IS NULL;",
    'ALTER TABLE osf_nodelog ALTER COLUMN created SET NOT NULL;',
    'ALTER TABLE osf_nodelog ALTER COLUMN modified SET NOT NULL;',
    "UPDATE osf_pagecounter SET created='epoch', modified='epoch' WHERE created IS NULL;",
    "ALTER TABLE osf_pagecounter ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_pagecounter ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_alternativecitation ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_alternativecitation ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_apioauth2application ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_apioauth2personaltoken ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_apioauth2personaltoken ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_apioauth2scope ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_apioauth2scope ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_archivejob ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_archivejob ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_archivetarget ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_archivetarget ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_citationstyle ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_citationstyle ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_conference ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_conference ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_draftregistration ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_draftregistration ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_draftregistrationapproval ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_draftregistrationapproval ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_draftregistrationlog ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_draftregistrationlog ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_embargo ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_embargo ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_embargoterminationapproval ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_embargoterminationapproval ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_externalaccount ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_externalaccount ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_identifier ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_identifier ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_institution ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_institution ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_mailrecord ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_mailrecord ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_metaschema ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_metaschema ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_nodelicense ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_nodelicense ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_nodelicenserecord ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_nodelicenserecord ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_noderelation ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_noderelation ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_notificationdigest ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_notificationdigest ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_notificationsubscription ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_notificationsubscription ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_osfuser ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_osfuser ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_preprintprovider ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_preprintprovider ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_privatelink ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_queuedmail ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_queuedmail ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_registrationapproval ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_registrationapproval ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_retraction ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_retraction ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_subject ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_subject ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_tag ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_tag ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_useractivitycounter ADD COLUMN created timestamp with time zone;",
    "ALTER TABLE osf_useractivitycounter ADD COLUMN modified timestamp with time zone;",
    "ALTER TABLE osf_abstractnode RENAME COLUMN date_created TO created;",
    "ALTER TABLE osf_abstractnode RENAME COLUMN date_modified TO modified;",
    "ALTER TABLE osf_apioauth2application RENAME COLUMN date_created TO created;",
    "ALTER TABLE osf_comment RENAME COLUMN date_created TO created;",
    "ALTER TABLE osf_comment RENAME COLUMN date_modified TO modified;",
    "ALTER TABLE osf_fileversion RENAME COLUMN date_modified TO external_modified;",
    "ALTER TABLE osf_preprintservice RENAME COLUMN date_created TO created;",
    "ALTER TABLE osf_preprintservice RENAME COLUMN date_modified TO modified;",
    "ALTER TABLE osf_privatelink RENAME COLUMN date_created TO created;",
    "ALTER TABLE osf_session RENAME COLUMN date_created TO created;",
    "ALTER TABLE osf_session RENAME COLUMN date_modified TO modified;",
    """
    UPDATE osf_abstractnode
    SET last_logged=(
        SELECT date
        FROM osf_nodelog
        WHERE node_id = "osf_abstractnode"."id"
        ORDER BY date DESC
        LIMIT 1)
    WHERE (SELECT COUNT(id) FROM osf_nodelog WHERE node_id = "osf_abstractnode"."id" LIMIT 1) > 0;
    """,
    """
    UPDATE osf_abstractnode
    SET last_logged=modified
    WHERE (SELECT COUNT(id) FROM osf_nodelog WHERE node_id = "osf_abstractnode"."id" LIMIT 1) = 0;
    """,
    "UPDATE osf_alternativecitation SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_apioauth2application SET modified='epoch';",
    "UPDATE osf_apioauth2personaltoken SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_apioauth2scope SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_archivejob SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_archivetarget SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_citationstyle SET created=date_parsed, modified='epoch';",
    "UPDATE osf_conference SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_draftregistration SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_draftregistrationapproval SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_draftregistrationlog SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_embargo SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_embargoterminationapproval SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_externalaccount SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_identifier SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_institution SET created='epoch', modified='epoch';",
    "UPDATE osf_mailrecord SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_metaschema SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_nodelicense SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_nodelicenserecord SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    """
    UPDATE osf_noderelation SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch'
    WHERE LENGTH(_id) > 5;
    UPDATE osf_noderelation SET created='epoch', modified='epoch'
    WHERE LENGTH(_id) <= 5;
    """,
    "UPDATE osf_notificationdigest SET created=timestamp, modified='epoch';",
    "UPDATE osf_notificationsubscription SET created='epoch', modified='epoch';",
    "UPDATE osf_osfuser SET created='epoch', modified='epoch';",
    "UPDATE osf_preprintprovider SET created='epoch', modified='epoch';",
    "UPDATE osf_privatelink SET modified='epoch';",
    "UPDATE osf_queuedmail SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_registrationapproval SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_retraction SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_subject SET created=TO_TIMESTAMP(('x' || SUBSTR(_id, 1, 8))::bit(32)::int)::timestamptz, modified='epoch';",
    "UPDATE osf_tag SET created='epoch', modified='epoch';",
    "UPDATE osf_useractivitycounter SET created='epoch', modified='epoch';",
    "ALTER TABLE osf_alternativecitation ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_alternativecitation ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_apioauth2application ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_apioauth2personaltoken ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_apioauth2personaltoken ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_apioauth2scope ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_apioauth2scope ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_archivejob ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_archivejob ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_archivetarget ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_archivetarget ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_citationstyle ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_citationstyle ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_conference ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_conference ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_draftregistration ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_draftregistration ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_draftregistrationapproval ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_draftregistrationapproval ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_draftregistrationlog ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_draftregistrationlog ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_embargo ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_embargo ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_embargoterminationapproval ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_embargoterminationapproval ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_externalaccount ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_externalaccount ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_identifier ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_identifier ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_institution ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_institution ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_mailrecord ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_mailrecord ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_metaschema ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_metaschema ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_nodelicense ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_nodelicense ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_nodelicenserecord ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_nodelicenserecord ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_noderelation ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_noderelation ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_notificationdigest ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_notificationdigest ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_notificationsubscription ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_notificationsubscription ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_osfuser ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_osfuser ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_preprintprovider ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_preprintprovider ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_privatelink ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_queuedmail ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_queuedmail ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_registrationapproval ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_registrationapproval ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_retraction ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_retraction ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_subject ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_subject ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_tag ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_tag ALTER COLUMN modified SET NOT NULL;",
    "ALTER TABLE osf_useractivitycounter ALTER COLUMN created SET NOT NULL;",
    "ALTER TABLE osf_useractivitycounter ALTER COLUMN modified SET NOT NULL;"
]

@celery_app.task
def run_sql(sql):
    table = sql.split(' ')[5]
    logger.info('Updating table {}'.format(table))
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()
            if not rows:
                raise Exception('Sentry notification that {} is migrated'.format(table))

@celery_app.task(name='scripts.premigrate_created_modified')
def migrate():
    # Note:
    # To update data slowly without requiring lots of downtime,
    # add the following to CELERYBEAT_SCHEDULE in website/settings:
    #
    #   '1-minute-incremental-migrations':{
    #       'task': 'scripts.premigrate_created_modified',
    #       'schedule': crontab(minute='*/1'),
    #   },
    #
    # And let it run for about a week
    for statement in POPULATE_COLUMNS:
        run_sql.delay(statement)

def add_columns():
    for statement in ADD_COLUMNS:
        with connection.cursor() as cursor:
            cursor.execute(statement)

def finalize_migration():
    for statement in FINALIZE_MIGRATION:
        with connection.cursor() as cursor:
            cursor.execute(statement)

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
    parser.add_argument(
        '--start',
        action='store_true',
        dest='start',
        help='Adds columns',
    )
    parser.add_argument(
        '--finish',
        action='store_true',
        dest='finish',
        help='Sets NOT NULL',
    )
    pargs = parser.parse_args()
    if pargs.start and pargs.finish:
        raise Exception('Cannot start and finish in the same run')
    with transaction.atomic():
        if pargs.start:
            add_columns()
        elif pargs.finish:
            raise Exception('Not until data is migrated')
            finalize_migration()
        else:
            raise Exception('Must specify start or finish')
        if pargs.dry_run:
            raise Exception('Dry Run -- Transaction aborted.')

if __name__ == '__main__':
    main()
