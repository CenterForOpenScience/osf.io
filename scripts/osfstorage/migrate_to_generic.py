from __future__ import unicode_literals

import sys
import logging
import datetime
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from scripts import utils as script_utils

from framework.transactions.context import TokuTransaction

from website.files import models
from website.app import init_app
from website.addons.osfstorage import model as osfstorage_model

NOW = datetime.datetime.utcnow()
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
    logger.info('Migration: OsfStorageFileNode -> FileNode')
    migrate_filenodes()
    logger.info('Migration: OsfStorageTrashedFileNode -> TrashedFileNode')
    migrate_trashedfilenodes()

    logger.info('Checking that all Files have been migrated...')
    diff = osfstorage_model.OsfStorageFileNode.find().count() - models.FileNode.find().count()
    if diff > 0:
        logger.error('Missing {} FileNodes; canceling transaction')
        raise Exception('{} unmigrated FileNodes'.format(diff))

    logger.info('Checking that all File versions have been migrated...')
    diff = osfstorage_model.OsfStorageFileVersion.find().count() - models.FileVersion.find().count()
    if diff != 0:
        logger.error('{} OsfStorageFileVersions did not get migrated'.format(diff))
        logger.error('This is most likely because they are orphaned')
        logger.error('This is not a show stopper; The migration was still successful')
    else:
        logger.info('Migration successful')


def migrate_trashedfilenodes():
    for trashed in osfstorage_model.OsfStorageTrashedFileNode.find():
        logger.debug('Migrating OsfStorageTrashedFileNode {}'.format(trashed._id))

        if trashed.node_settings is None:
            logger.warning('OsfStorageTrashedFileNode {} has no node_settings; skipping'.format(trashed._id))
            continue

        parent_id = trashed.to_storage()['parent']
        parent = osfstorage_model.OsfStorageTrashedFileNode.load(parent_id) or osfstorage_model.OsfStorageFileNode.load(parent_id)
        if parent:
            if isinstance(parent, osfstorage_model.OsfStorageFileNode):
                parent = (parent._id, 'storedfilenode')
            else:
                parent = (parent._id, 'trashedfilenode')

        models.TrashedFileNode(
            _id=trashed._id,
            versions=translate_versions(trashed.versions),
            node=trashed.node_settings.owner,
            parent=parent,
            is_file=trashed.kind == 'file',
            provider='osfstorage',
            name=trashed.name,
            path='/' + trashed._id + ('' if trashed.kind == 'file' else '/'),
            materialized_path=''
        ).save()


def migrate_filenodes():
    for node_settings in paginated(osfstorage_model.OsfStorageNodeSettings):
        if node_settings.owner is None:
            logger.warning('OsfStorageNodeSettings {} has no parent; skipping'.format(node_settings._id))
            continue
        logger.info('Migrating files for {!r}'.format(node_settings.owner))

        listing = []
        for filenode in osfstorage_model.OsfStorageFileNode.find(Q('node_settings', 'eq', node_settings._id)):
            logger.debug('Migrating OsfStorageFileNode {}'.format(filenode._id))
            versions = translate_versions(filenode.versions)
            if filenode.is_file and not filenode.node.is_deleted:
                if not filenode.versions:
                    logger.warning('File {!r} has no versions'.format(filenode))
                elif not versions:
                    logger.warning('{!r} is a file with no translatable versions'.format(filenode))

            new_node = models.StoredFileNode(
                _id=filenode._id,
                versions=versions,
                node=node_settings.owner,
                parent=None if not filenode.parent else filenode.parent._id,
                is_file=filenode.kind == 'file',
                provider='osfstorage',
                name=filenode.name,
                last_touched=NOW
            )

            # Wrapped's save will populate path and materialized_path
            new_node.wrapped().save()
            listing.append(new_node)

        assert node_settings.get_root()
        for x in listing:
            # Make sure everything transfered properly
            if x.to_storage()['parent']:
                assert x.parent, '{!r}\'s parent {} does not exist'.format(x.wrapped(), x.to_storage()['parent'])


def translate_versions(versions):
    translated = []
    for index, version in enumerate(versions):
        if version is None:
            raise Exception('Version {} missing from database'.format(version))
        if not version.metadata or not version.location:
            logger.error('Version {} missing metadata or location'.format(version))
            continue
        translated.append(translate_version(version, index))
    return translated


def translate_version(version, index):
    version = models.FileVersion(
        _id=version._id,
        creator=version.creator,
        identifier=index + 1,
        date_created=version.date_created,
        location=version.location,
        metadata=version.metadata,
        size=version.size,
        content_type=version.content_type,
        date_modified=version.date_modified,
    )
    try:
        version.save()
    except KeyExistsException:
        version = models.FileVersion.load(version._id)

    return version


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
    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)
    main(dry=dry)
