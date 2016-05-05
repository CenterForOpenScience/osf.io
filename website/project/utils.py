# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from modularodm import Q

from website.project.model import Node

# Alias the project serializer
from website.project.views.node import _view_project
serialize_node = _view_project  # TODO: Seriously?

CONTENT_NODE_QUERY = (
    # Can encompass accessible projects, registrations, or forks
    Q('is_bookmark_collection', 'ne', True) &
    Q('is_collection', 'ne', True) &
    Q('is_deleted', 'eq', False)
)

PROJECT_QUERY = (
    # Excludes registrations
    CONTENT_NODE_QUERY &
    Q('is_registration', 'ne', True)
)

TOP_LEVEL_PROJECT_QUERY = (
    # Top level project is defined based on whether node (of any category) has a parent. Can include forks.
    Q('parent_node', 'eq', None) &
    PROJECT_QUERY
)


def recent_public_registrations(n=10):
    registrations = Node.find(
        CONTENT_NODE_QUERY &
        Q('parent_node', 'eq', None) &
        Q('is_public', 'eq', True) &
        Q('is_registration', 'eq', True)
    ).sort(
        '-registered_date'
    )
    for reg in registrations:
        if not n:
            break
        if reg.is_retracted or reg.is_pending_embargo:
            # Filter based on calculated properties
            continue
        n -= 1
        yield reg
