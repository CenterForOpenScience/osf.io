# -*- coding: utf-8 -*-
"""Backup and remove orphaned registrations and forks with corrupt git repos.
"""

import os
import logging
import subprocess

from website import settings
from website.app import init_app

from scripts.utils import (
    backup_node_git, backup_node_mongo,
)
from scripts.migrate_orphaned_clones import find_orphans


logger = logging.getLogger(__name__)


def check_node(node):
    """Check whether git repo for node is intact.
    """
    if not node.files_current:
        return True
    try:
        with open(os.devnull, 'w') as fnull:
            subprocess.check_call(
                ['git', 'log'],
                cwd=os.path.join(settings.UPLOADS_PATH, node._id),
                stdout=fnull,
                stderr=fnull,
            )
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError:
        return False


def find_corrupt_orphans():
    orphans = find_orphans()
    return [
        each for each in orphans
        if not check_node(each)
    ]


def migrate_orphan(orphan, dry_run=True):
    assert not check_node(orphan)
    logger.warn('Backing up and removing node {0}'.format(orphan._id))
    if not dry_run:
        backup_node_git(orphan)
        backup_node_mongo(orphan)


def main(dry_run=True):
    init_app()
    orphans = find_orphans()
    logger.warn(
        'Found {0} corrupted orphan nodes'.format(
            orphans.count()
        )
    )
    for orphan in orphans:
        migrate_orphan(orphan, dry_run=dry_run)


if __name__ == '__main__':
    import sys
    dry = 'dry' in sys.argv
    main(dry_run=dry)