# -*- coding: utf-8 -*-
import logging
from copy import deepcopy
import sys

from modularodm import Q

from framework.transactions.context import TokuTransaction
from website.app import init_app
from website.models import NodeLog
from scripts import utils as script_utils

logger = logging.getLogger(__name__)

def get_targets():
    return NodeLog.find(Q('action', 'eq', NodeLog.WIKI_DELETED))

def migrate(targets, dry_run=True):
    # iterate over targets
    count = 0
    for log in targets:
        node = log.node
        logger.debug('Checking node {}'.format(node._id))
        versions = node.wiki_pages_versions
        original_versions = deepcopy(versions)
        current = node.wiki_pages_current
        updated_versions = {}
        for wiki in versions:
            if wiki in current:
                updated_versions[wiki] = versions[wiki]

        if original_versions != updated_versions:
            logger.info('Updating wiki_pages_versions from {} to {}'.format(original_versions, updated_versions))
            node.wiki_pages_versions = updated_versions
            node.save()
            count += 1
    logger.info('Migrated {} nodes'.format(count))


def main():
    dry_run = False
    if '--dry' in sys.argv:
        dry_run = True
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate(targets=get_targets(), dry_run=dry_run)
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == '__main__':
    main()
