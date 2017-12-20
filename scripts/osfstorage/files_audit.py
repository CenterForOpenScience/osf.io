#!/usr/bin/env python
# encoding: utf-8

"""Verify that all OSF Storage files have Glacier backups and parity files,
creating any missing backups.

TODO: Add check against Glacier inventory
Note: Must have par2 installed to run
"""

from __future__ import division

import os
import math
import hashlib
import logging

import pyrax

from django.db import transaction
from botocore.utils import calculate_tree_hash
from pyrax.exceptions import NoSuchObject

from framework.celery_tasks import app as celery_app

from website.app import init_app
from osf.models import FileVersion

from scripts import utils as scripts_utils
from scripts.osfstorage import utils as storage_utils
from scripts.osfstorage import settings as storage_settings


GLACIER_PART_SIZE = 4 * (1024 * 1024)  # 4MB
GLACIER_SINGLE_OPERATION_THRESHOLD = 100 * (1024 * 1024)  # 100MB


class Context(object):
    def __init__(self):
        self.dry_run = True
        self.container_primary = None
        self.container_parity = None
        self.vault = None
        self.audit_temp_path = None


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.INFO)


def download_from_cloudfiles(ctx, version, path):
    file_path = os.path.join(path, version.location['object'])
    if os.path.exists(file_path):
        # We cannot assume the file is valid and not from a previous failure.
        os.remove(file_path)

    try:
        obj = ctx.container_primary.get_object(version.location['object'])
        with open(file_path, 'wb') as fp:
            hasher = hashlib.sha256()
            fetcher = obj.fetch(chunk_size=262144000)  # 256mb chunks
            while True:
                try:
                    chunk = next(fetcher)
                except StopIteration:
                    break
                hasher.update(chunk)
                fp.write(chunk)
        if hasher.hexdigest() != version.metadata['sha256']:
            raise Exception('SHA256 mismatch, cannot continue')
        return file_path
    except NoSuchObject as err:
        logger.error('*** FILE NOT FOUND ***')
        logger.error('Exception:')
        logger.exception(err)
        logger.error('Version info:')
        logger.error(version.to_storage())
        return None


def glacier_sync_multipart_upload(ctx, version, file_path, file_size):
    # Reference: https://boto3.readthedocs.io/en/latest/reference/services/glacier.html#Glacier.Vault.initiate_multipart_upload
    multipart_upload = ctx.vault.initiate_multipart_upload(
        archiveDescription=version.location['object'],
        partSize=str(GLACIER_PART_SIZE),
    )

    with open(file_path, 'rb') as fp:
        for byte_offset in range(0, file_size, GLACIER_PART_SIZE):
            part = fp.read(GLACIER_PART_SIZE)
            range_header = 'bytes {}-{}/{}'.format(byte_offset, byte_offset + len(part) - 1, file_size)
            multipart_upload.upload_part(
                range=range_header,
                body=part,
            )

    # TODO: Ideally this would be computed on upload, however this is also a good double check, so we do not incur any off-by-one issues.
    # see https://boto3.readthedocs.io/en/latest/reference/services/glacier.html#Glacier.MultipartUpload.complete
    checksum = calculate_tree_hash(open(file_path, 'rb'))
    response = multipart_upload.complete(
        archiveSize=str(file_size),
        checksum=checksum,
    )
    assert response['checksum'] == checksum

    return response['archiveId']


def ensure_glacier(ctx, version, path):
    if version.metadata.get('archive'):
        return

    logger.warn('Glacier archive for version {0} not found'.format(version._id))

    if ctx.dry_run:
        return

    file_path = download_from_cloudfiles(ctx, version, path)
    if file_path:
        file_size = os.path.getsize(file_path)
        if file_size > GLACIER_SINGLE_OPERATION_THRESHOLD:
            archive_id = glacier_sync_multipart_upload(ctx, version, file_path, file_size)
        else:
            with open(file_path, 'rb') as fp:
                archive = ctx.vault.upload_archive(
                    vaultName=storage_settings.GLACIER_VAULT_NAME,
                    archiveDescription=version.location['object'],
                    body=fp,
                )
                archive_id = archive.id
        with transaction.atomic():
            txn_version = FileVersion.objects.filter(_id=version._id).select_for_update().get()
            metadata = {
                'archive': archive_id,
                'vault': ctx.vault.name,
            }
            txn_version.update_metadata(metadata)
            txn_version.save()
        os.remove(file_path)


def ensure_parity(ctx, version, path):
    if version.metadata.get('parity'):
        return

    logger.warn('Parity files for version {0} not found'.format(version._id))

    if ctx.dry_run:
        return

    file_path = download_from_cloudfiles(ctx, version, path)
    if file_path:
        results = storage_utils.create_parity_files(file_path, redundancy=storage_settings.PARITY_REDUNDANCY)
        for parity_file_path in [r[0] for r in results]:
            ctx.container_parity.create(parity_file_path)
            os.remove(parity_file_path)
        with transaction.atomic():
            txn_version = FileVersion.objects.filter(_id=version._id).select_for_update().get()
            metadata = {
                'parity': {
                    'redundancy': storage_settings.PARITY_REDUNDANCY,
                    'files': [
                        {'name': os.path.split(r[0])[1], 'sha256': r[1]} for r in results
                    ]
                }
            }
            txn_version.update_metadata(metadata)
            txn_version.save()
        os.remove(file_path)


def audit_parity(ctx, num_of_workers, worker_id):
    targets = FileVersion.objects.filter(location__has_key='object', metadata__parity__isnull=True, size__gt=0)

    path = os.path.join(storage_settings.AUDIT_TEMP_PATH, str(worker_id), 'parity')
    try:
        os.makedirs(path)
    except OSError:
        pass

    est_max = math.ceil(targets.count() / num_of_workers)
    progress = scripts_utils.Progress(precision=0)
    progress.start(est_max, 'Parity {}'.format(worker_id))
    for version in targets.iterator():
        if hash(version._id) % num_of_workers == worker_id:
            if version.size == 0:
                continue
            ensure_parity(ctx, version, path)
            progress.increment()
    progress.stop()


def audit_glacier(ctx, num_of_workers, worker_id):
    targets = FileVersion.objects.filter(location__has_key='object', metadata__archive__isnull=True, size__gt=0)

    path = os.path.join(storage_settings.AUDIT_TEMP_PATH, str(worker_id), 'glacier')
    try:
        os.makedirs(path)
    except OSError:
        pass

    est_max = math.ceil(targets.count() / num_of_workers)
    progress = scripts_utils.Progress(precision=0)
    progress.start(est_max, 'Glacier {}'.format(worker_id))
    for version in targets.iterator():
        if hash(version._id) % num_of_workers == worker_id:
            if version.size == 0:
                continue
            ensure_glacier(ctx, version, path)
            progress.increment()
    progress.stop()


@celery_app.task(name='scripts.osfstorage.files_audit')
def main(num_of_workers=0, worker_id=0, glacier=True, parity=True, dry_run=True):
    # Set up storage backends
    init_app(set_backends=True, routes=False)

    ctx = Context()
    ctx.dry_run = dry_run

    try:
        # Authenticate to Rackspace
        pyrax.settings.set('identity_type', 'rackspace')
        pyrax.set_credentials(
            storage_settings.USERNAME,
            storage_settings.API_KEY,
            region=storage_settings.REGION
        )
        ctx.container_primary = pyrax.cloudfiles.get_container(storage_settings.PRIMARY_CONTAINER_NAME)
        ctx.container_parity = pyrax.cloudfiles.get_container(storage_settings.PARITY_CONTAINER_NAME)

        # Connect to AWS
        ctx.vault = storage_utils.get_glacier_resource().Vault(
            storage_settings.GLACIER_VAULT_ACCOUNT_ID,
            storage_settings.GLACIER_VAULT_NAME
        )

        # Log to file
        if not ctx.dry_run:
            scripts_utils.add_file_logger(logger, __file__, suffix=worker_id)

        if glacier:
            logger.info('files_audit: glacier audit start')
            audit_glacier(ctx, num_of_workers, worker_id)
            logger.info('files_audit: glacier audit complete')

        if parity:
            logger.info('files_audit: parity audit start')
            audit_parity(ctx, num_of_workers, worker_id)
            logger.info('files_audit: parity audit complete')

    except Exception as err:
        logger.error('=== Unexpected Error ===')
        logger.exception(err)
        raise err


if __name__ == '__main__':
    import sys
    arg_num_of_workers = int(sys.argv[1])
    arg_worker_id = int(sys.argv[2])
    arg_glacier = 'glacier' in sys.argv
    arg_parity = 'parity' in sys.argv
    arg_dry_run = 'dry' in sys.argv
    main(num_of_workers=arg_num_of_workers, worker_id=arg_worker_id, glacier=arg_glacier, parity=arg_parity, dry_run=arg_dry_run)
