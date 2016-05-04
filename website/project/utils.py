# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from modularodm import Q

from website.project.model import Node

# Alias the project serializer
from website.project.views.node import _view_project
serialize_node = _view_project

def recent_public_registrations(n=10):
    recent_query = (
        Q('parent_node', 'eq', None) &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False) &
        Q('is_collection', 'ne', True) &
        Q('is_bookmark_collection', 'ne', True)
    )
    registrations = Node.find(
        recent_query &
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
