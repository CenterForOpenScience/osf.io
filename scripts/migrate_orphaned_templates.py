# -*- coding: utf-8 -*-

import logging

from modularodm import Q

from framework.transactions.context import transaction

from website import models
from website.app import init_app


logger = logging.getLogger(__name__)


def find_orphans():
    """Find orphaned nodes created during templating.
    """
    return models.Node.find(
        Q('template_node', 'ne', None) &
        Q('category', 'ne', 'project') &
        Q('__backrefs.parent.node.nodes.0', 'exists', False) &
        Q('is_deleted', 'ne', True)
    )


def find_candidate_parents(node):
    """Find candidate parents for an orphaned node. Candidates must include a
    log with the template action created from the parent of the template node of
    the orphaned template. Candidates must also not include any child nodes
    templated from the template node of the orphan.
    """
    template = node.template_node
    if not template:
        return []
    logs = models.NodeLog.find(
        Q('action', 'eq', 'created_from') &
        Q('params.template_node.id', 'eq', node.template_node.parent_node._id)
    )
    return [
        each.node for each in logs
        if not any(child.template_node == template for child in each.node.nodes)
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