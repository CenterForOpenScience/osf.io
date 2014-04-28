"""
GitLab describes file revisions by branch and SHA; the original OSF files
describes versions by number (1, 2, 3, ...). This script builds a routing
table from original OSF files revision identifiers to GitLab SHAs. The table
is written to website/compat_file_routes.json.
"""

import os
import json
import logging

from website.app import init_app
from website.models import Node
from website import settings

from . import utils


app = init_app()
logger = logging.getLogger(__name__)

ROUTE_PATH = os.path.join(settings.BASE_PATH, 'compat_file_routes.json')


def build_node_urls(node):

    repo = utils.get_node_repo(node)

    if not repo:
        return

    table = {}

    for file in os.listdir(repo.path):

        if file == '.git':
            continue

        try:
            commits = list(repo.get_walker(paths=[file], reverse=True))
        except Exception as error:
            logger.error('Could not get repo')
            logger.exception(error)
            continue

        if len(commits) == 0:
            logger.error('File {0} has no commits'.format(file))
            continue

        commits = list(repo.get_walker(paths=[file], reverse=True))
        # Map version id => sha
        table[file] = {
            idx + 1: commit.commit.id
            for idx, commit in enumerate(commits)
        }
        # Route URLs with no version to latest commit
        table[file][None] = commits[-1].commit.id

    return table


def build_nodes_urls(outfile):
    """Write a json file mapping node IDs to the routing table for that node's
    files.
    """

    table = {}

    for node in Node.find():

        logger.warn('Building node {0}'.format(node._id))

        subtable = build_node_urls(node)

        if subtable:
            table[node._id] = subtable

    with open(outfile, 'w') as fp:
        json.dump(table, fp, indent=4)

    return table


if __name__ == '__main__':

    build_nodes_urls(outfile=ROUTE_PATH)
