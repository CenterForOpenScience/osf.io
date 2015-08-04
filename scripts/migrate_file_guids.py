import sys
import logging

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction
from framework.guid.model import Guid

from website.files import models
from website.addons.box.model import BoxFile
from website.addons.s3.model import S3GuidFile
from website.addons.dropbox.model import DropboxFile
from website.addons.github.model import GithubGuidFile
from website.addons.dataverse.model import DataverseFile
from website.addons.figshare.model import FigShareGuidFile
from website.addons.osfstorage.model import OsfStorageGuidFile
from website.addons.googledrive.model import GoogleDriveGuidFile

logger = logging.getLogger(__name__)


def do_migration():
    logger.info('Migrating OsfStorage Guids')
    migrate_osfstorage_guids()
    logger.info('Migrating Box Guids')
    migrate_guids(BoxFile, 'box')
    logger.info('Migrating S3 Guids')
    migrate_guids(S3GuidFile, 's3')
    logger.info('Migrating Dropbox Guids')
    migrate_guids(DropboxFile, 'dropbox')
    logger.info('Migrating Github Guids')
    migrate_guids(GithubGuidFile, 'github')
    logger.info('Migrating Dataverse Guids')
    migrate_guids(DataverseFile, 'dataverse')
    logger.info('Migrating figshare Guids')
    migrate_guids(FigShareGuidFile, 'figshare')
    logger.info('Migrating GoogleDrive Guids')
    migrate_guids(GoogleDriveGuidFile, 'googledrive')


def migrate_osfstorage_guids():
    for guid in OsfStorageGuidFile.find():
        referent = models.StoredFileNode.load(guid.waterbutler_path.strip('/'))
        if referent is None:
            logger.warning('OsfStorageGuidFile {} resolved to None; skipping'.format(guid._id))
            continue
        actual_guid = Guid.load(guid._id)
        assert actual_guid is not None
        actual_guid.referent = referent
        actual_guid.save()
        assert actual_guid._id == referent.get_guid()._id


def migrate_guids(guid_type, provider):
    for guid in guid_type.find():
        # Note: No metadata is populated here
        # It will be populated whenever this guid is next viewed
        if guid.node is None:
            logger.warning('{}({})\'s node is None; skipping'.format(guid_type, guid._id))
            continue

        models.StoredFileNode(
            is_file=True,
            node=guid.node,
            provider=provider,
            path=guid.waterbutler_path,
            name=guid.waterbutler_path,
            materialized_path=guid.waterbutler_path,
        ).save()


def main(dry=True):
    init_app(set_backends=True, routes=False)  # Sets the storage backends on all models
    with TokuTransaction():
        do_migration()
        if dry:
            raise Exception('Abort Transaction - Dry Run')


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    main(dry=dry)
