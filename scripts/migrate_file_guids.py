from __future__ import unicode_literals

import sys
import logging

from modularodm import Q
from modularodm import exceptions

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


def paginated(model, query=None, increment=200):
    last_id = ''
    pages = (model.find(query).count() / increment) + 1
    for i in xrange(pages):
        q = Q('_id', 'gt', last_id)
        if query:
            q &= query
        page = list(model.find(q).limit(increment))
        for item in page:
            yield item
        if page:
            last_id = item._id


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
    for guid in paginated(OsfStorageGuidFile):
        if '{{' in guid.waterbutler_path:
            logger.warning('OsfStorageGuidFile {} ({}) looks like a google bot link; skipping'.format(guid._id, guid.waterbutler_path.strip('/')))
            continue

        referent = models.StoredFileNode.load(guid.waterbutler_path.strip('/'))
        if referent is None:
            logger.warning('OsfStorageGuidFile {} ({}) resolved to None; skipping'.format(guid._id, guid.waterbutler_path.strip('/')))
            continue
        logger.debug('Migrating guid {}'.format(guid._id))
        actual_guid = Guid.load(guid._id)
        assert actual_guid is not None
        actual_guid.referent = referent
        actual_guid.save()
        # try:
        #     assert actual_guid._id == referent.get_guid()._id
        # except exceptions.MultipleResultsFound:
        #     logger.warning('FileNode {!r} has muliple guids referring to it.'.format(referent.wrapped()))


def migrate_guids(guid_type, provider):
    cls = models.FileNode.resolve_class(provider, models.FileNode.FILE)

    for guid in paginated(guid_type):
        # Note: No metadata is populated here
        # It will be populated whenever this guid is next viewed
        if guid.node is None:
            logger.warning('{}({})\'s node is None; skipping'.format(guid_type, guid._id))
            continue

        if guid.waterbutler_path in ('/{{ revision.osfDownloadUrl }}', '/{{ currentVersion().osfDownloadUrl }}', '/{{ currentVersion().osfDownloadUrl }}', '/{{ node.urls.files }}', '/{{ revision.extra.user.url }}'):
            logger.warning('{}({})\'s is a googlebot path; skipping'.format(guid_type, guid._id))
            continue

        logger.debug('Migrating guid {} ({})'.format(guid._id, guid.waterbutler_path))

        try:
            file_node = cls(
                node=guid.node,
                path=guid.waterbutler_path,
                name=guid.waterbutler_path,
                materialized_path=guid.waterbutler_path,
            )
            file_node.save()
        except exceptions.KeyExistsException:
            file_node = cls.find_one(
                Q('node', 'eq', guid.node) &
                Q('path', 'eq', guid.waterbutler_path)
            )
            logger.warning('{!r}({}) has multiple guids'.format(file_node.wrapped(), guid._id))

        actual_guid = Guid.load(guid._id)
        actual_guid.referent = file_node
        actual_guid.save()


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
