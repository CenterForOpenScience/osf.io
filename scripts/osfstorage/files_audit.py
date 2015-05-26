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
import logging

import pyrax
import progressbar
from modularodm import Q
from boto.glacier.layer2 import Layer2
from pyrax.exceptions import NoSuchObject

from website.app import init_app
from website.addons.osfstorage import model

from scripts import utils as scripts_utils
from scripts.osfstorage import utils as storage_utils
from scripts.osfstorage import settings as storage_settings


container_primary = None
container_parity = None
vault = None

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
logging.getLogger('boto').setLevel(logging.CRITICAL)


def download_from_cloudfiles(version):
    path = os.path.join(storage_settings.AUDIT_TEMP_PATH, version.location['object'])
    if os.path.exists(path):
        return path
    try:
        obj = container_primary.get_object(version.location['object'])
        obj.download(storage_settings.AUDIT_TEMP_PATH)
    except NoSuchObject as err:
        logger.error('*** FILE NOT FOUND ***')
        logger.error('Exception:')
        logger.exception(err)
        logger.error('Version info:')
        logger.error(version.to_storage())
    return path


def delete_temp_file(version):
    path = os.path.join(storage_settings.AUDIT_TEMP_PATH, version.location['object'])
    try:
        os.remove(path)
    except OSError:
        pass


def ensure_glacier(version, dry_run):
    if version.metadata.get('archive'):
        return
    logger.warn('Glacier archive for version {0} not found'.format(version._id))
    if dry_run:
        return
    download_from_cloudfiles(version)
    file_path = os.path.join(storage_settings.AUDIT_TEMP_PATH, version.location['object'])
    glacier_id = vault.upload_archive(file_path, description=version.location['object'])
    version.metadata['archive'] = glacier_id
    version.save()


def check_parity_files(version):
    index = list(container_parity.list_all(prefix='{0}.par2'.format(version.location['object'])))
    vols = list(container_parity.list_all(prefix='{0}.vol'.format(version.location['object'])))
    return len(index) == 1 and len(vols) >= 1


def ensure_parity(version, dry_run):
    if check_parity_files(version):
        return
    logger.warn('Parity files for version {0} not found'.format(version._id))
    if dry_run:
        return
    file_path = download_from_cloudfiles(version)
    parity_paths = storage_utils.create_parity_files(file_path)
    for parity_path in parity_paths:
        container_parity.create(parity_path)
        os.remove(parity_path)
    if not check_parity_files(version):
        logger.error('Parity files for version {0} not found after update'.format(version._id))


def ensure_backups(version, dry_run):
    if version.size == 0:
        return
    ensure_glacier(version, dry_run)
    ensure_parity(version, dry_run)
    delete_temp_file(version)


def get_targets():
    return model.OsfStorageFileVersion.find(
        Q('status', 'ne', 'cached') &
        Q('location.object', 'exists', True)
    )


def main(nworkers, worker_id, dry_run):
    targets = get_targets()
    progress_bar = progressbar.ProgressBar(maxval=math.ceil(targets.count() / nworkers)).start()
    idx = 0
    for version in targets:
        if hash(version._id) % nworkers == worker_id:
            ensure_backups(version, dry_run)
            idx += 1
            progress_bar.update(idx)
    progress_bar.finish()


if __name__ == '__main__':
    import sys
    nworkers = int(sys.argv[1])
    worker_id = int(sys.argv[2])
    dry_run = 'dry' in sys.argv

    # Set up storage backends
    init_app(set_backends=True, routes=False)

    try:
        # Authenticate to Rackspace
        pyrax.settings.set('identity_type', 'rackspace')
        pyrax.set_credentials(
            storage_settings.USERNAME,
            storage_settings.API_KEY,
            region=storage_settings.REGION
        )
        container_primary = pyrax.cloudfiles.get_container(storage_settings.PRIMARY_CONTAINER_NAME)
        container_parity = pyrax.cloudfiles.get_container(storage_settings.PARITY_CONTAINER_NAME)

        # Connect to AWS
        layer2 = Layer2(
            aws_access_key_id=storage_settings.AWS_ACCESS_KEY,
            aws_secret_access_key=storage_settings.AWS_SECRET_KEY,
        )
        vault = layer2.get_vault(storage_settings.GLACIER_VAULT)

        # Log to file
        if not dry_run:
            scripts_utils.add_file_logger(logger, __file__, suffix=worker_id)
            main(nworkers, worker_id, dry_run=dry_run)
    except Exception as err:
        logger.error('=== Unexpected Error ===')
        logger.exception(err)
        raise err
