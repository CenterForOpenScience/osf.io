from __future__ import division
from __future__ import unicode_literals

import logging
import datetime as dt

from pymongo.errors import DuplicateKeyError

from modularodm import Q
from modularodm.storage.base import KeyExistsException

from framework.mongo import database
from framework.analytics import clean_page
from framework.transactions.context import TokuTransaction

from scripts import utils as scripts_utils

from website.app import init_app
from website.project.model import NodeLog
from website.addons.osfstorage import model
from website.addons.osfstorage import oldels

logger = logging.getLogger(__name__)


LOG_ACTIONS = [
    'osf_storage_file_added',
    'osf_storage_file_updated',
    'osf_storage_file_removed',
    'osf_storage_file_restored',
    'file_added',
    'file_updated',
    'file_removed',
    'file_restored',
]


def migrate_download_counts(node, children, dry=True):
    collection = database['pagecounters']
    updates = []

    for old_path, new in children.items():
        if dry:
            # Note in dry mode new is None
            new_id = ':'.join(['download', node._id, 'new_id'])
            old_id = ':'.join(['download', node._id, old_path])
        else:
            new_id = ':'.join(['download', node._id, new._id])
            old_id = ':'.join(['download', node._id, old_path])

        result = collection.find_one({'_id': clean_page(old_id)})

        if not result:
            continue

        logger.info('Copying download counts of {!r} to {!r}'.format(old_path, new))

        if not dry:
            result['_id'] = new_id
            updates.append(result)
            # try:
            #     # database.pagecounters.insert(result)
            # except DuplicateKeyError:
            #     logger.warn('Already migrated {!r}'.format(old_path))
            #     continue
        else:
            continue

        for idx in range(len(new.versions)):
            result = collection.find_one({'_id': clean_page('{}:{}'.format(old_id, idx + 1))})
            if not result:
                continue

            logger.info('Copying download count of version {} of {!r} to version {} of {!r}'.format(idx + 1, old_path, idx, new))
            if not dry:
                result['_id'] = '{}:{}'.format(new_id, idx)
                updates.append(result)
                # database.pagecounters.insert(result)

        if not dry:
            try:
                database.pagecounters.insert(updates, continue_on_error=True)
            except DuplicateKeyError:
                pass

def migrate_node_settings(node_settings, dry=True):
    logger.info('Running `on add` for node settings of {}'.format(node_settings.owner._id))

    if not dry:
        node_settings.on_add()


def migrate_file(node, old, parent, dry=True):
    assert isinstance(old, oldels.OsfStorageFileRecord)
    if not dry:
        try:
            new = parent.append_file(old.name)
            logger.debug('Created new child {}'.format(old.name))
        except KeyExistsException:
            logger.warning('{!r} has already been migrated'.format(old))
            return parent.find_child_by_name(old.name)
        new.versions = old.versions
        new.is_deleted = old.is_deleted
        new.save()
    else:
        new = None
    return new

def migrate_logs(node, children, dry=True):
    for log in NodeLog.find(Q('params.node', 'eq', node._id)):
        if log.action not in LOG_ACTIONS:
            continue

        if log.params.get('_path') is not None and log.params.get('_urls'):
            logger.warning('Log for file {} has already been migrated'.format(log.params['path']))
            continue

        if dry:
            logger.debug('{!r} {} -> {}'.format(log, log.params['path'], 'New path'))
            continue

        try:
            new = children[log.params['path']]
        except KeyError:
            if not log.params['path'].startswith('/'):
                logger.warning('Failed to migrate log with path {}'.format(log.params['path']))
            continue

        mpath = new.materialized_path()
        url = '/{}/files/osfstorage/{}/'.format(node._id, new._id)
        logger.debug('{!r} {} -> {}'.format(log, log.params['path'], mpath))

        log.params['_path'] = mpath
        log.params['_urls'] = {
            'view': url,
            'download': url + '?action=download'
        }

        log.save()

    NodeLog._cache.clear()


def migrate_guids(node_settings, children, dry=True):
    for guid in model.OsfStorageGuidFile.find(
            Q('node', 'eq', node_settings.owner) & Q('_has_no_file_tree', 'ne', True)):
        if guid._path is not None:
            logger.warn('File guid {} has already been migrated'.format(guid._id))
            continue

        logger.info('Migrating file guid {}'.format(guid._id))
        if not dry:
            try:
                guid._path = children[guid.path].path
            except KeyError:
                if not guid.path.startswith('/'):
                    # A number of invalid GUIDs were generated by
                    # search bots that spidered invalid URLs
                    # e.g. /blah/{{ urls.revisions }}
                    # which created OsfStorageGuidFile records
                    # that are not included in the file_tree for
                    # a node's OsfStorageNodeSettings
                    # Any file Guid whose path contains a '/' should
                    # be considered invalid, and we skip over those and mark them so that
                    # the rest of the migration can occur
                    logger.warning('Skipping invalid OsfStorageGuidFile with _id {} and path {}. Marking as invalid...'.format(guid._id, guid.path))
                    guid._has_no_file_tree = True
                    guid.save()
                else:
                    logger.warning('Already migrated {!r}'.format(guid))
                continue
            guid.save()
    model.OsfStorageGuidFile._cache.clear()


def migrate_children(node_settings, dry=True):
    if not node_settings.file_tree:
        return logger.warning('Skipping node {}; file_tree is None'.format(node_settings.owner._id))

    logger.info('Migrating children of node {}'.format(node_settings.owner._id))

    children = {}
    for x in node_settings.file_tree.children:
        n = migrate_file(node_settings.owner, x, node_settings.root_node, dry=dry)
        if n:  # not migrated yet
            children[x.path] = n

    migrate_logs(node_settings.owner, children, dry=dry)
    migrate_guids(node_settings, children, dry=dry)
    migrate_download_counts(node_settings.owner, children, dry=dry)
    del children


def main(nworkers, worker_id, dry=True):
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info('Not running in dry mode, changes WILL be made')
    else:
        logger.info('Running in dry mode, changes NOT will be made')

    to_migrate = model.OsfStorageNodeSettings.find(Q('_migrated_from_old_models', 'ne', True))
    if to_migrate.count() == 0:
        logger.info('No nodes to migrate; exiting...')
        return

    failed = 0
    logger.info('Found {} nodes to migrate'.format(to_migrate.count()))

    for node_settings in to_migrate:
        if hash(node_settings._id) % nworkers != worker_id:
            continue

        try:
            with TokuTransaction():
                migrate_node_settings(node_settings, dry=dry)
                migrate_children(node_settings, dry=dry)
                if not dry:
                    node_settings.reload()
                    node_settings._migrated_from_old_models = True
                    node_settings.save()
        except Exception as error:
            logger.error('Could not migrate file tree from {}'.format(node_settings.owner._id))
            logger.exception(error)
            failed += 1

    if failed > 0:
        logger.error('Failed to migrate {} nodes'.format(failed))

# Migrate file guids
# db.osfstorageguidfile.update({
#   '_path': {'$ne': null}
# }, {
#     $rename:{'path': 'premigration_path'}
# }, {multi: true})

# db.osfstorageguidfile.update({
#   '_path': {'$ne': null}
# }, {
#     $rename:{'_path': 'path'}
# }, {multi: true})


# Migrate logs
# db.nodelog.update({
#   'params._path': {'$ne': null}
# }, {
#     $rename:{'params.path': 'params.premigration_path'}
# }, {multi: true})

# db.nodelog.update({
#   'params._path': {'$ne': null}
# }, {
#     $rename:{'params._path': 'params.path'}
# }, {multi: true})

# db.nodelog.update({
#   'params._urls': {'$ne': null}
# }, {
#     $rename:{'params.urls': 'params.premigration_urls'}
# }, {multi: true})

# db.nodelog.update({
#   'params._urls': {'$ne': null}
# }, {
#     $rename:{'params._urls': 'params.urls'}
# }, {multi: true})

if __name__ == '__main__':
    import sys

    nworkers = int(sys.argv[1])
    worker_id = int(sys.argv[2])

    dry = 'dry' in sys.argv

    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)

    init_app(set_backends=True, routes=False)
    main(nworkers, worker_id, dry=dry)
