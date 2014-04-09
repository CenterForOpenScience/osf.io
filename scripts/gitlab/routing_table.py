"""
GitLab describes file revisions by branch and SHA; the original OSF files
describes versions by number (1, 2, 3, ...). This script builds a routing
table from original OSF files revision identifiers to GitLab SHAs. The table
is written to website/compat_file_routes.json.
"""

import os
import json
import logging
from dulwich.repo import Repo
from dulwich.errors import NotGitRepository

from website.app import init_app
from website.models import Node
from website import settings


app = init_app()
logger = logging.getLogger(__name__)

ROUTE_PATH = os.path.join(settings.BASE_PATH, 'compat_file_routes.json')


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


def build_nodes_urls(outfile):

    table = {}

    for node in Node.find():

        subtable = build_node_urls(node)

        if subtable:
            table[node._id] = subtable

    with open(outfile, 'w') as fp:
        json.dump(table, fp, indent=4)

    return table


if __name__ == '__main__':

    build_nodes_urls(outfile=ROUTE_PATH)
