#!/usr/bin/env python
# encoding: utf-8

from __future__ import division
from __future__ import unicode_literals

import re
import copy
import math
import logging
import progressbar

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.storage.base import KeyExistsException

from framework.mongo import database
from framework.transactions.context import TokuTransaction

from scripts import utils as scripts_utils

from website.app import init_app
from website.project.model import NodeLog
from website.addons.osfstorage import model, oldels

logger = logging.getLogger(__name__)


def migrate_download_counts(node, old, new, dry=True):
    escaped_old_path = old.path.replace('.', '_').replace('$', '_')

    if dry:
        new_id = ':'.join(['download', node._id, 'new id'])
    else:
        new_id = ':'.join(['download', node._id, new._id])

    old_id = ':'.join(['download', node._id, escaped_old_path])
    escaped_id = ':'.join(['download', node._id, re.escape(escaped_old_path)])

    for doc in database.pagecounters.find({'_id': {'$regex': '^{}(:\d+)?'.format(escaped_id)}}):
        new_doc = copy.deepcopy(doc)
        assert old_id in doc['_id']
        if len(doc['_id'].split(':')) < 4:
            new_doc['_id'] = doc['_id'].replace(old_id, new_id)
        else:
            version = int(doc['_id'].split(':')[-1])
            assert version > 0
            logger.debug('Decrementing version {} to {}'.format(version, version - 1))
            new_doc['_id'] = doc['_id'].replace('{}:{}'.format(old_id, version), '{}:{}'.format(new_id, version - 1))

        logger.debug('{} -> {}'.format(doc, new_doc))
        if not dry:
            database.pagecounters.insert(new_doc)
            database.pagecounters.remove(doc['_id'])


def migrate_node_settings(node_settings, dry=True):
    logger.info('Running `on add` for node settings of {}'.format(node_settings.owner._id))

    if not dry:
        node_settings.on_add()

def migrate_file(node, old, parent, dry=True):
    assert isinstance(old, oldels.OsfStorageFileRecord)
    logger.debug('Creating new child {}'.format(old.name))
    if not dry:
        try:
            new = parent.append_file(old.name)
        except KeyExistsException:
            logger.warning('{!r} has already been migrated'.format(old))
            return
        new.versions = old.versions
        new.is_deleted = old.is_deleted
        new.save()
    else:
        new = None

    migrate_guid(node, old, new, dry=dry)
    migrate_log(node, old, new, dry=dry)
    migrate_download_counts(node, old, new, dry=dry)


LOG_ACTIONS = set([
    'osf_storage_file_added',
    'osf_storage_file_updated',
    'osf_storage_file_removed',
    'osf_storage_file_restored',
    'file_added',
    'file_updated',
    'file_removed',
    'file_restored',
])
def migrate_log(node, old, new, dry=True):
    res = NodeLog.find(
        (
            Q('params.node', 'eq', node._id) |
            Q('params.project', 'eq', node._id)
        ) &
        Q('params.path', 'eq', old.path)
    )

    res = [each for each in res if each.action in LOG_ACTIONS]

    if res:
        logger.info('Migrating {} logs for {!r} in {!r}'.format(len(res), old, node))
    else:
        logger.debug('No logs to migrate for {!r} in {!r}'.format(len(res), old, node))

    for log in res:
        if dry:
            logger.debug('{!r} {} -> {}'.format(log, log.params['path'], 'New path'))
        else:
            logger.debug('{!r} {} -> {}'.format(log, log.params['path'], new.materialized_path()))
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
        logger.debug('No guids found for {}'.format(old.path))
        return

    if not dry:
        guid.path = new.path
        guid.save()

def migrate_children(node_settings, dry=True):
    if not node_settings.file_tree:
        logger.warning('Skipping node {}; file_tree is None'.format(node_settings.owner._id))
        return

    logger.info('Migrating children of node {}'.format(node_settings.owner._id))
    for child in node_settings.file_tree.children:
        migrate_file(node_settings.owner, child, node_settings.root_node, dry=dry)


def main(nworkers, worker_id, dry=True, catchup=True):
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
        logger.info('Not running in dry mode, changes WILL be made')
    else:
        logger.info('Running in dry mode, changes NOT will be made')

    if catchup:
        logger.info('Running in catchup mode, looping over ALL OsfStorageNodeSettings objects')
        to_migrate = model.OsfStorageNodeSettings.find()
    else:
        to_migrate = model.OsfStorageNodeSettings.find(Q('root_node', 'eq', None))

    if to_migrate.count() == 0:
        logger.info('No nodes to migrate; exiting...')
        return

    count = 0
    failed = 0
    logger.info('Found {} nodes to migrate'.format(to_migrate.count()))
    progress_bar = progressbar.ProgressBar(maxval=math.ceil(to_migrate.count() / nworkers)).start()

    for node_settings in to_migrate:
        if hash(node_settings._id) % nworkers != worker_id:
            continue

        try:
            with TokuTransaction():
                migrate_node_settings(node_settings, dry=dry)
                migrate_children(node_settings, dry=dry)
            count += 1
            progress_bar.update(count)
        except Exception as error:
            logger.error('Could not migrate file tree from {}'.format(node_settings.owner._id))
            logger.exception(error)
            failed += 1

    progress_bar.finish()
    if failed > 0:
        logger.error('Failed to migrate {} nodes'.format(failed))


if __name__ == '__main__':
    import sys

    nworkers = int(sys.argv[1])
    worker_id = int(sys.argv[2])

    dry = 'dry' in sys.argv
    catchup = 'catchup' in sys.argv

    if 'debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif 'info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif 'error' in sys.argv:
        logger.setLevel(logging.ERROR)

    with init_app(set_backends=True, routes=True).test_request_context():
        main(nworkers, worker_id, dry=dry, catchup=catchup)
