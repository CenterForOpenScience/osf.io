"""
Scripts to identify and repair corrupted git repos using ``git fsck``.
"""

import os
import logging
import subprocess

from framework.mongo import StoredObject

from website import settings
from website.models import Node
from website.app import init_app

from .recover import restore_repo


app = init_app('website.settings', set_backends=True, routes=True)


def fsck_node(node):
    """Check whether a node's git repo has been corrupted.

    :param Node node:

    :returns: Status code if corrupted, else ``False``

    """
    path = os.path.join(settings.UPLOADS_PATH, node._id)
    if not os.path.exists(path):
        return False
    try:
        subprocess.check_output(
            ['git', 'fsck'],
            stderr=subprocess.STDOUT,
            cwd=path,
        )
    except subprocess.CalledProcessError as error:
        return error.output
    return False


def fsck_nodes(restore=False):
    """List and optionally store corrupted git repos.

    :param bool restore: Attempt to restore corrupted repos

    """
    errors = {}
    for node in Node.find():
        output = fsck_node(node)
        if output:
            logging.warn('Found corrupt repo at {0}'.format(node._id))
            errors[node._id] = output
            if restore:
                logging.warn('Restoring repo')
                restore_repo(node)
        StoredObject._clear_caches()
    return errors


if __name__ == '__main__':

    # Collect arguments
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--restore', action='store_true')
    args = parser.parse_args()

    # Run
    fsck_nodes(args.restore)
