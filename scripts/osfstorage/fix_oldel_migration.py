# -*- coding: utf-8 -*-
"""Nodes that were updated between the first run of migrate_from_oldels and the catchup run
of migrate_from_oldels will have logs that were unmigrated because the _migrated_from_old_models
flag was set during the first migration.
"""
import datetime as dt
import logging
import sys

from modularodm import Q
from website.models import NodeLog, Node
from website.app import init_app
from framework.transactions.context import TokuTransaction

from . import migrate_from_oldels

logger = logging.getLogger(__name__)

def find_unmigrated_nodes():
    logs = NodeLog.find(Q('date', 'gt', dt.datetime(year=2015, month=4, day=26)) &
                        Q('date', 'lt', dt.datetime(year=2015, month=4, day=29)) &
                        Q('action', 'in', list(migrate_from_oldels.LOG_ACTIONS)))
    node_ids = set(sum([(each.params['node'], each.params['project']) for each in logs], tuple()))
    return (Node.load(node_id) for node_id in node_ids if node_id is not None)


def main(dry=True):
    count = 0
    for node in find_unmigrated_nodes():
        count += 1
        addon = node.get_addon('osfstorage')
        with TokuTransaction():
            migrate_from_oldels.migrate_children(addon, dry=dry)
    logger.info('Migrated {} nodes'.format(count))


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    init_app(mfr=False, set_backends=True)
    main(dry=dry)
