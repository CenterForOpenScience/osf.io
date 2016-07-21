# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from modularodm import Q

from website.project.model import Node
from website.project import signals
from framework.postcommit_tasks.handlers import run_postcommit
from framework.celery_tasks import app
from datetime import datetime
# Alias the project serializer
from website.project.views.node import _view_project
serialize_node = _view_project  # Not recommended practice

CONTENT_NODE_QUERY = (
    # Can encompass accessible projects, registrations, or forks
    # Note: is_bookmark collection(s) are implicitly assumed to also be collections; that flag intentionally omitted
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


@signals.node_updated.connect
def update_date_modified_for_users(node):
    update_date_modified_task(node._id)


@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def update_date_modified_task(node_id):
    node = Node.load(node_id)
    now = datetime.utcnow()
    for contrib in node.contributors:
        contrib.date_modified = now
        contrib.save()