"""
GitLab describes file revisions by branch and SHA; the original OSF files
describes versions by number (1, 2, 3, ...). This script builds a routing
table from original OSF files revision identifiers to GitLab SHAs. The table
is written to website/compat_file_routes.json.
"""

import os
import copy
import json
import logging
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository

from framework.mongo import db
from framework.analytics import sorted_qs

from website.app import init_app
from website.models import Node
from website import settings

from . import utils


app = init_app()
logger = logging.getLogger(__name__)

counters = db['pagecounters']


def migrate_counter(record):

    _, node_id, file_path, version_id = record['_id'].split(':')

    node = Node.load(node_id)
    repo = utils.get_node_repo(node)

    commits = list(repo.get_walker(paths=[file_path], reverse=True))
    try:
        sha = commits[version_id + 1].commit.id
    except IndexError:
        logging.warn('Could not find version {0} on {1}: {2}'.format(
            version_id, node._id, file_path
        ))
        return

    new_record = copy.deepcopy(record)
    new_record['_id'] = 'download:{0}:{1}:{2}'.format(
        node._id, file_path, sorted_qs({
            'branch': 'master',
            'sha': sha,
        })
    )

    counters.insert(new_record)


def migrate_counters():

    cursor = counters.find({
        '_id': {
            '$regex': r'^download:.*?:.*?:',
        }
    })

    for record in cursor:
        migrate_counter(record)

def build_node_urls(node):

    if not node.files_current:
        return {}

    path = os.path.join(settings.UPLOADS_PATH, node._id)

    if not os.path.exists(path):
        logger.warn('No folder found for node {0}'.format(node._id))
        return {}

    try:
        repo = Repo(path)
    except NotGitRepository:
        logger.warn('No repo found for node {0}'.format(node._id))
        return {}

    table = {}

    for file in os.listdir(path):

        if file == '.git':
            continue

        commits = list(repo.get_walker(paths=[file], reverse=True))
        table[file] = {
            idx + 1: commit.commit.id
            for idx, commit in enumerate(commits)
        }
        table[file][None] = commits[-1].commit.id

    return table



if __name__ == '__main__':

    pass
