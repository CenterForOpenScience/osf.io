"""
GitLab describes file revisions by branch and SHA; the original OSF files
describes versions by number (1, 2, 3, ...). This script builds a routing
table from original OSF files revision identifiers to GitLab SHAs. The table
is written to website/compat_file_routes.json.
"""

import os
import logging
import pymongo

from framework.mongo import StoredObject, db

from website.app import init_app
from website.models import Node

from . import utils


app = init_app()
logger = logging.getLogger(__name__)

route_collection = db['gitlab-compat-routes']


def build_node_urls(node):

    path = utils.get_node_path(node)

    if not os.path.exists(path):
        return

    git_commits = utils.get_commits(node)
    mongo_commits = utils.get_mongo_commits(node)

    # Note: Database inconsistencies arise periodically, so we can't trust
    # the SHAs stored in mongo. Only trust the stored SHAs if the sets of the
    # mongo SHAs and the git SHAs are the same.
    trust_mongo = set(git_commits) == set(sum(mongo_commits.values(), []))

    table = {}

    for file in os.listdir(path):

        if file == '.git':
            continue

        clean_file = file.replace('.', '_')
        if trust_mongo and clean_file in mongo_commits:
            commits = mongo_commits[file.replace('.', '_')]
        else:
            commits = utils.get_commits(node, file)

        if len(commits) == 0:
            logger.error('File {0}/{1} has no commits'.format(node._id, file))
            continue

        # Map version id => sha
        table[file] = {
            idx + 1: commit
            for idx, commit in enumerate(commits)
        }
        # Route URLs with no version to latest commit
        table[file][None] = commits[-1]

    # Prevent cache from exploding
    StoredObject._clear_caches()

    return table


def build_nodes_urls():
    """Write a json file mapping node IDs to the routing table for that node's
    files.

    """
    for node in Node.find():

        logger.warn('Building node {0}'.format(node._id))

        table = build_node_urls(node)

        try:
            route_collection.insert({
                '_id': node._id,
                'routes': table,
            })
        except pymongo.errors.DuplicateKeyError as error:
            logger.exception(error)


if __name__ == '__main__':
    build_nodes_urls()
