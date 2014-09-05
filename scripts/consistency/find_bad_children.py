"""Check for consistency errors in parent-child relationships.

"""
import logging

from website.app import init_app
from website import models
from framework import Q


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARN)
file_logger = logging.FileHandler('consistency/children.log')
logger.addHandler(file_logger)

app = init_app()


def find_orphaned_children(filters=None):
    """Find parents that don't point to their children.

    """
    errors = []
    query = Q('__backrefs.parent.node.nodes.0', 'exists', True)
    if filters:
        query = query & filters
    with_parent = models.Node.find(query)
    for child in with_parent:
        if len(child.node__parent) > 1:
            msg = u'Inconsistency: Child {} ({}) has {} parents.'.format(
                child.title,
                child._primary_key,
                len(child.node__parent),
            )
            logger.error(msg)
            errors.append(msg)
            continue
        parent = child.node__parent[0]
        if child not in parent.nodes:
            msg = u'Inconsistency: Parent {} ({}) does not point to child {} ({})'.format(
                parent.title,
                parent._primary_key,
                child.title,
                child._primary_key,
            )
            logger.error(msg)
            errors.append(msg)
    return errors


def find_missing_children(filters=None):
    """Find children that don't point to their parents.

    """
    errors = []
    query = Q('nodes.0', 'exists', True)
    if filters:
        query = query & filters
    with_children = models.Node.find(query)
    for parent in with_children:
        for child in parent.nodes:
            if not child.node__parent or child.node__parent[0] != parent:
                msg = u'Inconsistency: Child {} ({}) does not point to parent {} ({})'.format(
                    child.title,
                    child._primary_key,
                    parent.title,
                    parent._primary_key,
                )
                logger.error(msg)
                errors.append(msg)
    return errors


if __name__ == '__main__':
    errors = find_missing_children()
    errors = find_orphaned_children()
