import sys
import logging
from modularodm import Q
from modularodm.storage.base import KeyExistsException

from website.app import init_app
from scripts import utils as script_utils
from framework.transactions.context import TokuTransaction

from website.files import models
from website.addons.osfstorage import model as osfstorage_model

logger = logging.getLogger(__name__)


def do_migration():
    logger.info('Migration: OsfStorageFileNode -> FileNode')
    migrate_filenodes()
    logger.info('Migration: OsfStorageTrashedFileNode -> TrashedFileNode')
    migrate_trashedfilenodes()

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

        parent = osfstorage_model.OsfStorageTrashedFileNode.load(trashed.to_storage()['parent'])
        if parent is None:
            parent = osfstorage_model.OsfStorageFileNode.load(trashed.to_storage()['parent'])

        if trashed.node_settings is None:
            logger.warning('OsfStorageTrashedFileNode {} has no node_settings; skipping'.format(trashed._id))
            continue

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
    for node_settings in osfstorage_model.OsfStorageNodeSettings.find():
        if node_settings.owner is None:
            logger.warning('OsfStorageNodeSettings {} has no parent; skipping'.format(node_settings._id))
            continue
        logger.info('Migrating files for {}'.format(node_settings.owner.title))
        root_node = osfstorage_model.OsfStorageFileNode.load(node_settings.to_storage()['root_node'])
        if root_node is None:
            logger.warning('OsfStorageNodeSettings {} has no root_node; skipping'.format(node_settings._id))
            continue
        list(osfstorage_model.OsfStorageFileNode.find(Q('node_settings', 'eq', node_settings._id)))
        node_settings.root_node = migrate_top_down(node_settings, root_node)
        node_settings.save()


def migrate_top_down(node_settings, filenode, parent=None):
    logger.debug('Migrating OsfStorageFileNode {}'.format(filenode._id))
    new_node = models.StoredFileNode(
        _id=filenode._id,
        versions=translate_versions(filenode.versions),
        node=node_settings.owner,
        parent=parent,
        is_file=filenode.kind == 'file',
        provider='osfstorage',
        name=filenode.name,
    )

    # Wrapped's save will populate path and materialized_path
    new_node.wrapped().save()

    if filenode.is_folder:
        for child in filenode.children:
            migrate_top_down(node_settings, child, parent=new_node)

    return new_node

def translate_versions(versions):
    translated = []
    for index, version in enumerate(versions):
        if version is None:
            raise Exception('Version {} missing from database'.format(tuple(versions)[index]))
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
    main(dry=dry)
