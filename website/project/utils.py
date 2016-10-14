# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from django.db.models import F
from modularodm import Q

from website.project.model import Node

# Alias the project serializer
from website.project.views.node import _view_project
serialize_node = _view_project  # Not recommended practice

CONTENT_NODE_QUERY = (
    # Can encompass accessible projects, registrations, or forks
    # Note: is_bookmark collection(s) are implicitly assumed to also be collections; that flag intentionally omitted
    Q('is_deleted', 'eq', False)
)

PROJECT_QUERY = CONTENT_NODE_QUERY

TOP_LEVEL_PROJECT_QUERY = (
    # Top level project is defined based on whether its root is itself, i.e. it has no parents
    Q('root_id', 'eq', F('id')) &
    PROJECT_QUERY
)


def recent_public_registrations(n=10):
    registrations = Node.find(
        CONTENT_NODE_QUERY &
        Q('root_id', 'eq', F('id')) &
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
