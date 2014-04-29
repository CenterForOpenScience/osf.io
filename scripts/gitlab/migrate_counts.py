#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Migrate OsfGuidFile's download counts to GitlabGuidFile download counts.
"""

import os
import copy
import logging

from framework.mongo import db

from website.app import init_app
from website.models import Node

from . import utils


app = init_app()
logger = logging.getLogger(__name__)

counters = db['pagecounters']


def migrate_counter(record):
    """Migrate analytics for OSF file downloads to GitLab file downloads.
    OSF file download counts are stored with keys of format <path>:<vid> Gitlab
    counts are stored with keys of format <path>:<sha>.

    """

    logger.warn('Migrating counter {0}'.format(record['_id']))

    _, node_id, file_path, version_id = record['_id'].split(':')

    # Catch ObjectId keys
    try:
        version_id = int(version_id)
    except:
        return

    node = Node.load(node_id)
    if not node:
        logger.warn('Node {0} not found'.format(node_id))
        return

    path = utils.get_node_path(node)

    if not os.path.exists(path):
        return

    files = os.listdir(path)
    raw_path = next((file for file in files if file.replace('.', '_') == file_path), None)
    if not raw_path:
        logger.error('Could not find file {0}'.format(file_path))

    commits = utils.get_commits(node, raw_path)
    try:
        sha = commits[version_id - 1]
    except IndexError:
        logging.warn('Could not find version {0} on {1}: {2}'.format(
            version_id, node._id, file_path
        ))
        return

    _id = 'download:{0}:{1}:{2}'.format(
        node._id, file_path, sha
    )
    counters.remove({'_id': _id})
    new_record = copy.deepcopy(record)
    new_record['_id'] = _id

    counters.insert(new_record)


def migrate_counters():
    """Batch migrate download counters."""
    cursor = counters.find({
        '_id': {
            '$regex': r'^download:.*?:.*?:',
        }
    })

    for record in cursor:
        migrate_counter(record)


if __name__ == '__main__':
    migrate_counters()
