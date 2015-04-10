import copy
import logging

from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from scripts import utils as scripts_utils

from website.app import init_app
from website.addons.osfstorage import model, oldels

logger = logging.getLogger(__name__)


def migrate_download_counts(node, old, new, dry=True):
    collection = database['pagecounters']

    new_id = ':'.join(['download', node._id, new._id])
    old_id = ':'.join(['download', node._id, old.path])

    for doc in collection.find({'_id': {'$regex': '^{}(:\d)?'.format(old_id)}}):
        new_doc = copy.deep(doc)
        doc['_id'] = doc['_id'].replace(old_id, new_id)
        collection.update(doc, new_doc)


def migrate_node_settings(node_settings, dry=True):
    logger.info('Running `on add` for node settings of {}'.format(node_settings.owner._id))

    if not dry:
        node_settings.on_add()

def migrate_file(node, old, parent, dry=True):
    assert isinstance(old, oldels.OsfStorageFileRecord)
    logger.info('Creating new child {}'.format(old.name))
    if not dry:
        new = parent.append_file(old.name)
        new.versions = old.versions
        new.is_deleted = old.is_deleted
    else:
        new = None

    migrate_guid(node, old, new, dry=dry)
    migrate_log(node, old, new, dry=dry)
    migrate_download_counts(node, old, new, dry=dry)


def migrate_log(node, old, new, dry=True):
    res = NodeLog.find(
        (
            Q('params.node', 'eq', node._id) |
            Q('params.project', 'eq', node._id)
        ) &
        Q('params.path', 'eq', old.path) &
        Q('action', 'istartswith', 'osf_storage_file')
    )
    logger.info('Migrating {} logs for {!r} in {!r}'.format(res.count(), old, node))

    for log in res:
        logger.info('{!r} {} -> {}'.format(log, log.params['path'], new.materialized_path()))
        if not dry:
            log.params['path'] = new.materialized_path()
            url = node.web_url_for(
                'addon_view_or_download_file',
                path=new.path.strip('/'),
                provider='osfstorage'
            )
            log.params['urls'] = {
                'view': url,
                'download': url + '?action=download'
            }
            log.save()


def migrate_guid(node, old, new, dry=True):
    try:
        guid = model.OsfStorageGuidFile.find_one(
            Q('node', 'eq', node) &
            Q('path', 'eq', old.path)
        )
        logger.info('Migrating file guid {}'.format(guid._id))
    except NoResultsFound:
        logger.info('No guids found for {}'.format(new.path))
        return

    if not dry:
        guid.path = new.path
        guid.save()

def migrate_children(node_settings, dry=True):
    if not node_settings.file_tree:
        logger.info('Skipping node {}; file_tree is None', node_settings.owner._id)

    logger.info('Migrating children of node {}', node_settings.owner._id)
    for child in node_settings.file_tree.children:
        migrate_file(node_settings.owner, child, node_settings.root_node, dry=dry)


def main(dry=True):
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)

    for node_settings in model.OsfStorageNodeSettings.find():
        try:
            with TokuTransaction():
                migrate_node_settings(node_settings, dry=dry)
                migrate_children(node_settings, dry=dry)
        except Exception as error:
            logger.error('Could no migrate file tree from {}'.format(node_settings.owner._id))
            logger.exception(error)


if __name__ == '__main__':
    import sys
    dry = 'dry' in sys.argv
    init_app(set_backends=True, routes=False)
    main(dry=dry)
