"""Check for consistency errors in parent-child relationships.

"""

from website.app import init_app
from website import models
from framework import Q

app = init_app()

def find_orphaned_children():
    """Find parents that don't point to their children.

    """
    with_parent = models.Node.find(
        Q('__backrefs.parent.node.nodes', 'nin', [None, []])
    )
    for child in with_parent:
        if len(child.node__parent) != 1:
            print 'Inconsistency: Child {} ({}) has {} parents.'.format(
                child.title,
                child._primary_key,
                len(child.node__parent),
            )
            continue
        parent = child.node__parent[0]
        if child not in parent.nodes:
            print 'Inconsistency: Parent {} ({}) does not point to child {} ({})'.format(
                parent.title,
                parent._primary_key,
                child.title,
                child._primary_key,
            )

def find_missing_children():
    """Find children that don't point to their parents.

    """
    with_children = models.Node.find(
        Q('nodes', 'ne', [])
    )
    for parent in with_children:
        for child in parent.nodes:
            if not child.node__parent or child.node__parent[0] != parent:
                print 'Inconsistency: Child {} ({}) does not point to parent {} ({})'.format(
                    child.title,
                    child._primary_key,
                    parent.title,
                    parent._primary_key,
                )

if __name__ == '__main__':
    find_missing_children()
    find_orphaned_children()
