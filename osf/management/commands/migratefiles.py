import base64
import hashlib
import itertools
import logging
import os
import time
import shutil
import tempfile

import pyrax

from django.core.management import BaseCommand
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.db import connection, transaction
from django.db.models import F
from django.db.models.expressions import RawSQL
from google.cloud import storage as gc_storage
from google.api_core import exceptions as gc_exceptions

from osf.models.files import FileVersion
from api.base.celery import app
from scripts.osfstorage import settings as storage_settings

logger = logging.getLogger(__name__)

# WARNING: Currently the script assumes object names are globally unique and there is only
# a single storage provider which is osf storage. Care needs to be taken if this script
# is ever evaluated to run after StorageProviders have been introduced into the schema.

CHUNK_SIZE = 256 * (1024 * 1024)  # 256MB


class Context(object):
    def __init__(self):
        self.dry = False
        self.async = False
        self.batch_size = 0
        self.limit = 0
        self.container = None


class Command(BaseCommand):
    help = 'Migrates files from Rackspace Cloud Files to Google Cloud Storage'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry',
            help='Dry run',
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            dest='sync',
            help='Phase 1: Synchronize files',
        )
        parser.add_argument(
            '--migration',
            action='store_true',
            dest='migration',
            help='Phase 2: Migrate database records',
        )
        parser.add_argument(
            '--reverse-migration',
            action='store_true',
            dest='reverse_migration',
            help='Phase 2: Reverse migrate database records',
        )
        # parser.add_argument(
        #     '--cleanup',
        #     action='store_true',
        #     dest='cleanup',
        #     help='Phase 3: Cleanup the database records',
        # )
        parser.add_argument(
            '--purge-container',
            action='store',
            dest='purge_container',
            type=str,
            default=None,
            help='Phase 3: Purge Rackspace CloudFiles container',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            dest='async',
            help='Run operations as celery tasks',
        )
        parser.add_argument(
            '--batch-size',
            action='store',
            dest='batch_size',
            type=int,
            default=100,
            help='Number of operations to perform per task',
        )
        parser.add_argument(
            '--limit',
            action='store',
            dest='limit',
            type=int,
            default=0,
            help='Number of iterations to run, defaults to 0 or unlimited',
        )

    def handle(self, *args, **options):
        ctx = Context()
        ctx.dry = options['dry']
        ctx.async = options['async']
        ctx.batch_size = options['batch_size']
        ctx.limit = options['limit']
        ctx.container = options['purge_container']

        if options['sync']:
            synchronize(ctx)
        elif options['migration']:
            migration(ctx)
        elif options['reverse_migration']:
            reverse_migration(ctx)
        elif options['purge_container']:
            purge_container(ctx)
        # elif options['cleanup']:
        #     cleanup(ctx)


def purge_container(ctx):
    logger.info('Started purge of container %s', ctx.container)

    if ctx.dry:
        return

    pyrax.settings.set('identity_type', 'rackspace')
    pyrax.set_credentials(
        storage_settings.USERNAME,
        storage_settings.API_KEY,
        region=storage_settings.REGION
    )
    rs_container = pyrax.cloudfiles.get_container(ctx.container)

    counter = 1
    deleters = []
    marker = ''
    files = rs_container.list_object_names(limit=ctx.batch_size, marker=marker)
    while files:
        marker = files[-1]
        deleter = pyrax.cloudfiles.bulk_delete(rs_container, files, async=True)
        deleters.append(deleter)
        counter = counter + 1
        if ctx.limit and counter > ctx.limit:
            break
        files = rs_container.list_object_names(limit=ctx.batch_size, marker=marker)

    while deleters:
        for deleter in deleters:
            if deleter.completed:
                print(deleter.results)
                deleters.remove(deleter)
        if deleters:
            logger.info('Waiting on %d deleters for container %s', len(deleters), ctx.container)
            time.sleep(10)

    logger.info('Finished purge of container %s', ctx.container)


# def cleanup(ctx):
#     if ctx.dry:
#         return
#
#     logger.info('Starting cleanup [SQL]:')
#
#     with connection.cursor() as cursor:
#         cursor.execute("""
#             UPDATE osf_fileversion
#             SET
#                 location = subquery.location
#                 , metadata = subquery.metadata
#             FROM
#                 (
#                     SELECT
#                         id
#                         , (
#                             location
#                             - 'container'
#                         ) AS location
#                         , (
#                             metadata
#                             - 'gcs_migration'
#                         ) AS metadata
#                     FROM
#                         osf_fileversion
#                     WHERE
#                         metadata->>'provider' = 'googlecloud'
#                         AND metadata ? 'gcs_migration'
#                 ) AS subquery
#             WHERE
#               osf_fileversion.id = subquery.id;
#         """, [])
#
#     logger.info('Finished cleanup [SQL]:')


def reverse_migration(ctx):
    qs = (
        FileVersion.objects
            .filter(metadata__has_key='gcs_migration', metadata__gcs_migration__has_key='complete')
    )

    logger.info('Found %d file versions to reverse migrate', qs.count())

    if ctx.dry:
        return

    logger.info('Starting reverse migration [SQL]:')

    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE osf_fileversion
            SET
                location = subquery.location
                , metadata = subquery.metadata
            FROM
                (
                    SELECT
                        id
                        , (
                            location
                            || '{"service": "cloudfiles"}'::jsonb
                            || '{"provider": "cloudfiles"}'::jsonb
                        ) AS location
                        , (
                            (
                                metadata
                                || '{"provider": "cloudfiles"}'::jsonb
                            )
                            #- '{gcs_migration,complete}'
                        ) AS metadata
                    FROM
                        osf_fileversion
                    WHERE
                        metadata ? 'gcs_migration'
                        AND metadata->'gcs_migration' ? 'complete'
                ) AS subquery
            WHERE
              osf_fileversion.id = subquery.id;
        """, [])

    logger.info('Finished reverse migration [SQL]:')


def migration(ctx):
    qs = (
        FileVersion.objects
            .filter(metadata__has_key='gcs_migration')
            .exclude(metadata__gcs_migration__has_key='complete')
    )

    logger.info('Found %d file versions to migrate', qs.count())

    if ctx.dry:
        return

    logger.info('Starting migration [SQL]:')

    with connection.cursor() as cursor:
        cursor.execute("""
            UPDATE osf_fileversion
            SET
                location = subquery.location
                , metadata = subquery.metadata
            FROM
                (
                    SELECT
                        id
                        , (
                            location
                            || '{"service": "googlecloud"}'::jsonb
                            || '{"provider": "googlecloud"}'::jsonb
                            || ('{"bucket": ' || (metadata->'gcs_migration'->'bucket')::text || '}')::jsonb
                        ) AS location
                        , (
                            metadata
                            || jsonb_build_object('extra', metadata->'extra'
                                || ('{"generation":' || (metadata->'gcs_migration'->'generation')::text || '}')::jsonb
                                || jsonb_build_object('hashes',
                                    (
                                        CASE WHEN metadata->'extra' ? 'hashes' THEN
                                            metadata->'extra'->'hashes' || ('{"crc32c":' || (metadata->'gcs_migration'->'crc32c')::text || '}')::jsonb
                                        ELSE
                                            ('{"crc32c":' || (metadata->'gcs_migration'->'crc32c')::text || '}')::jsonb
                                            ||  ('{"md5":' || (metadata->'gcs_migration'->'md5')::text || '}')::jsonb
                                        END
                                    )
                                )
                            )
                            || '{"provider": "googlecloud"}'::jsonb
                            || jsonb_build_object('gcs_migration', metadata->'gcs_migration'
                                || '{"complete": true}'::jsonb
                            )
                        ) AS metadata
                    FROM
                        osf_fileversion
                    WHERE
                        metadata ? 'gcs_migration'
                        AND NOT metadata->'gcs_migration' ? 'complete'
                ) AS subquery
            WHERE
              osf_fileversion.id = subquery.id;
        """, [])

    logger.info('Finished migration [SQL]:')


def synchronize(ctx):
    qs = (
        FileVersion.objects
            .filter(basefilenode__provider='osfstorage')
            .annotate(loc_obj=KeyTextTransform('object', 'location'))
            .distinct('loc_obj')
            .exclude(metadata__has_key='gcs_migration')
            .order_by()
    )

    logger.info('Found %d file versions to synchronize', qs.count())

    if ctx.dry:
        return

    counter = 1
    for file_versions in grouper(ctx.batch_size, qs):
        logger.info('Starting synchronizing files task %d for %d items', counter, len(file_versions))
        sync_args = ([i.id for i in file_versions],)
        if not ctx.async:
            synchronize_files.apply(args=sync_args)
        else:
            synchronize_files.apply_async(args=sync_args)
        counter = counter + 1
        if ctx.limit and counter > ctx.limit:
            return


@app.task(max_retries=0, ignore_result=True)
def synchronize_files(version_ids):
    pyrax.settings.set('identity_type', 'rackspace')
    pyrax.set_credentials(
        storage_settings.USERNAME,
        storage_settings.API_KEY,
        region=storage_settings.REGION
    )
    rs_container = pyrax.cloudfiles.get_container(storage_settings.PRIMARY_CONTAINER_NAME)

    gcs_client = gc_storage.Client.from_service_account_json(storage_settings.GCS_SERVICE_ACCOUNT_JSON)
    gcs_bucket = gcs_client.bucket(storage_settings.GCS_BUCKET_NAME)
    gcs_backup_bucket = gcs_client.bucket(storage_settings.GCS_BACKUP_BUCKET_NAME)

    temp_dir = tempfile.mkdtemp()

    for version_id in version_ids:
        file_version = FileVersion.objects.get(id=version_id)
        object_name = file_version.location['object']

        existing_file_version = (
            FileVersion.objects
                .filter(basefilenode__provider='osfstorage')
                .filter(location__object=object_name)
                .filter(metadata__has_key='gcs_migration')
                .order_by()
                .first()
        )

        # Perform the migration only if no existing migration exists in the database.
        if existing_file_version:
            file_version = existing_file_version
            logger.info('Already transferred version of object %s', object_name)
        else:
            # Upload the object to the primary Google Cloud Storage bucket
            gcs_chunk_size = None
            if file_version.metadata['size'] > CHUNK_SIZE:
                gcs_chunk_size = CHUNK_SIZE
            gcs_blob = gc_storage.Blob(object_name, gcs_bucket, chunk_size=gcs_chunk_size)
            gcs_backup_blob = gc_storage.Blob(object_name, gcs_backup_bucket, chunk_size=gcs_chunk_size)

            if gcs_blob.exists() and gcs_backup_blob.exists():
                gcs_blob.reload()
                object_size = gcs_blob.size
            else:
                # Download the object from Rackspace Cloud Files, and verify its sha256.
                logger.debug('RS: starting download for %s', object_name)
                path = os.path.join(temp_dir, object_name)
                if object_name == 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855':  # empty sha256
                    open(path, 'wb').close()
                    object_size = 0
                else:
                    object = rs_container.get_object(object_name)
                    with open(path, 'wb') as fp:
                        hasher = hashlib.sha256()
                        fetcher = object.fetch(chunk_size=CHUNK_SIZE)
                        while True:
                            try:
                                chunk = next(fetcher)
                            except StopIteration:
                                break
                            hasher.update(chunk)
                            fp.write(chunk)
                    assert hasher.hexdigest() == file_version.metadata['sha256']
                    object_size = os.path.getsize(path)
                logger.debug('RS: downloaded object %s, size %d bytes', object_name, object_size)

                # Upload the object to the primary Google Cloud Storage bucket
                try:
                    logger.debug('GCS: uploading to bucket %s, object %s', storage_settings.GCS_BUCKET_NAME, object_name)
                    gcs_blob.upload_from_filename(path)
                    assert base64.b64decode(gcs_blob.md5_hash).encode('hex') == file_version.metadata['md5']
                    logger.debug('GCS: finished upload to bucket %s, object %s', storage_settings.GCS_BUCKET_NAME, object_name)
                except gc_exceptions.Forbidden as ex:
                    # It is less calls to attempt the upload, than it is to check if the object exists.
                    logger.debug('GCS: object exists in bucket %s, loading metadata for %s', storage_settings.GCS_BUCKET_NAME, object_name)
                    gcs_blob.reload()

                # Upload the object to the backup Google Cloud Storage bucket
                try:
                    logger.debug('GCS: uploading to bucket %s, object %s', storage_settings.GCS_BACKUP_BUCKET_NAME, object_name)
                    gcs_backup_blob.upload_from_filename(path)
                    assert base64.b64decode(gcs_backup_blob.md5_hash).encode('hex') == file_version.metadata['md5']
                    logger.debug('GCS: finished upload to bucket %s, object %s', storage_settings.GCS_BACKUP_BUCKET_NAME, object_name)
                except gc_exceptions.Forbidden as ex:
                    # It is less calls to attempt the upload, than it is to check if the object exists.
                    pass

                # Delete the local file.
                os.remove(path)

            # Record the transfer in all versions of the file (exclude previously updated records).
            logger.debug('DB: updating file version %s migration metadata for object %s', version_id, object_name)
            with transaction.atomic():
                metadata = FileVersion.objects.filter(id=version_id).select_for_update().values_list('metadata', flat=True).get()
                metadata['gcs_migration'] = {
                    'bucket': storage_settings.GCS_BUCKET_NAME,
                    'backup_bucket': storage_settings.GCS_BACKUP_BUCKET_NAME,
                    'crc32c_b64': gcs_blob.crc32c,
                    'crc32c': base64.b64decode(gcs_blob.crc32c).encode('hex'),
                    'etag_b64': gcs_blob.etag,
                    'etag': base64.b64decode(gcs_blob.etag).encode('hex'),
                    'generation': gcs_blob.generation,
                    'md5_b64': gcs_blob.md5_hash,
                    'md5': base64.b64decode(gcs_blob.md5_hash).encode('hex'),
                }
                FileVersion.objects.filter(id=version_id).update(metadata=metadata)

            logger.info('Successfully transferred object %s, size %d bytes', object_name, object_size)

        # Reload the file version so we can copy its specific gcs metadata.
        file_version.reload()

        # Record the transfer in all versions of the file (exclude previously updated records).
        with transaction.atomic():
            metadata_qs = (
                FileVersion.objects
                    .filter(basefilenode__provider='osfstorage')
                    .filter(location__object=object_name)
                    .exclude(metadata__has_key='gcs_migration')
                    .order_by()
                    .select_for_update()
                    .values_list('id', 'metadata')
            )
            metadata_count = metadata_qs.count()
            if metadata_count:
                logger.info('DB: updating %s additional file version(s) migration metadata matching object %s', metadata_count, object_name)
                for (file_version_id, metadata) in metadata_qs.iterator():
                    metadata['gcs_migration'] = file_version.metadata['gcs_migration']
                    FileVersion.objects.filter(id=file_version_id).update(metadata=metadata)

    # Cleanup the temporary folder
    shutil.rmtree(temp_dir)


# Iterate an iterator by chunks (of n) in Python?
# source: https://stackoverflow.com/a/8991553
def grouper(n, iterable):
    if hasattr(iterable, 'iterator'):
        it = iterable.iterator()
    else:
        it = iter(iterable)
    while True:
       chunk = tuple(itertools.islice(it, n))
       if not chunk:
           return
       yield chunk
