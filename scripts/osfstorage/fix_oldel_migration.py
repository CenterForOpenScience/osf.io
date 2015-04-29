# -*- coding: utf-8 -*-
"""Nodes that were updated between the first run of migrate_from_oldels and the catchup run
of migrate_from_oldels will have logs that were unmigrated because the _migrated_from_old_models
flag was set during the first migration.
"""
import datetime as dt
import logging
import sys

from modularodm import Q
from website.models import NodeLog
from framework.transactions.context import TokuTransaction

from . import migrate_from_oldels

logger = logging.getLogger(__name__)

def find_unmigrated_nodes():
    logs = NodeLog.find(Q('date', 'gt', dt.datetime(year=2015, month=4, day=26)) &
                        Q('date', 'lt', dt.datetime(year=2015, month=4, day=29)) &
                        Q('action', 'in', list(migrate_from_oldels.LOG_ACTIONS)))
    nodes = set(sum([(each.params['node'], each.params['project']) for each in logs], tuple()))
    return [node for node in nodes if node is not None]


def main(dry=True):
    for node in find_unmigrated_nodes():
        addon = node.get_addon('osfstorage')
        with TokuTransaction():
            migrate_from_oldels.migrate_children(addon, dry=dry)


if __name__ == '__main__':
    dry = 'dry' in sys.argv
    main(dry=dry)
