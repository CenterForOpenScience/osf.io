# -*- coding: utf-8 -*-
"""Migrate orphaned registrations and forks. Try to indentify a single
candidate parent, matched by the creation log of the node and its cloned date.
"""

import logging

from modularodm import Q
from dateutil.relativedelta import relativedelta

from framework.transactions.context import transaction

from website import models
from website.app import init_app


logger = logging.getLogger(__name__)

# Current harakiri setting in uwsgi
OFFSET = relativedelta(seconds=60)


def find_orphans():
    """Find orphaned nodes that are registrations or forks.
    """
    return models.Node.find(
        Q('category', 'ne', 'project') &
        Q('__backrefs.parent.node.nodes.0', 'exists', False) &
        (
            Q('is_registration', 'eq', True) |
            Q('is_fork', 'eq', True)
        ) &
        Q('is_deleted', 'ne', True)

    )


def find_candidate_parents(node):
    """Find candidate parents for an orphaned node. Candidates must include the
    creation log of the orphan in their `logs` list, must be projects, must not
    be the orphaned node itself, must have the same cloning method as the
    orphan (registered, forked), must be created at approximately the same time
    as the orphan, and must not include any other clones of the orphan in their
    `nodes` lists.
    """
    if not node.logs:
        return []
    if not (node.is_fork or node.is_registration):
        return []
    query = (
        Q('_id', 'ne', node._id) &
        Q('category', 'eq', 'project') &
        Q('logs', 'eq', node.logs[0]._id)
    )
    if node.is_fork:
        query = (
            query &
            Q('is_fork', 'eq', True) &
            Q('forked_date', 'lte', node.forked_date) &
            Q('forked_date', 'gte', node.forked_date - OFFSET)
        )
    if node.is_registration:
        query = (
            query &
            Q('is_registration', 'eq', True) &
            Q('registered_date', 'lte', node.registered_date) &
            Q('registered_date', 'gte', node.registered_date - OFFSET)
        )
    candidates = models.Node.find(query)
    return [
        each for each in candidates
        if not any(node.logs[0] in child.logs for child in each.nodes)
    ]


@transaction()
def migrate_orphan(orphan, dry_run=True):
    parents = find_candidate_parents(orphan)
    if len(parents) == 1:
        parent = parents[0]
        logger.warn(
            'Adding component {0} to `nodes` list of project {1}'.format(
                orphan._id,
                parent._id,
            )
        )
        if not dry_run:
            parent.nodes.append(orphan)
            parent.save()
        return True
    return False


def main(dry_run=True):
    init_app()
    orphans = find_orphans()
    logger.warn(
        'Found {0} orphaned nodes'.format(
            orphans.count()
        )
    )
    count = 0
    for orphan in orphans:
        rescued = migrate_orphan(orphan, dry_run=dry_run)
        if rescued:
            count = 1
    logger.warn('Rescued {0} orphans'.format(count))


if __name__ == '__main__':
    import sys
    dry = 'dry' in sys.argv
    main(dry_run=dry)