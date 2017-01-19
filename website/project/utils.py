# -*- coding: utf-8 -*-
"""Various node-related utilities."""
from django.apps import apps
from modularodm import Q

from website import settings

from keen import KeenClient


# Alias the project serializer

def serialize_node(*args, **kwargs):
    from website.project.views.node import _view_project
    return _view_project(*args, **kwargs)  # Not recommended practice

CONTENT_NODE_QUERY = (
    # Can encompass accessible projects, registrations, or forks
    # Note: is_bookmark collection(s) are implicitly assumed to also be collections; that flag intentionally omitted
    Q('is_deleted', 'eq', False) &
    Q('type', 'ne', 'osf.collection')
)

PROJECT_QUERY = CONTENT_NODE_QUERY


def recent_public_registrations(n=10):
    Registration = apps.get_model('osf.Registration')
    registrations = Registration.find(
        CONTENT_NODE_QUERY &
        Q('is_public', 'eq', True)
    ).get_roots().sort(
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


def get_keen_activity():
    client = KeenClient(
        project_id=settings.KEEN['public']['project_id'],
        read_key=settings.KEEN['public']['read_key'],
    )

    node_pageviews = client.count(
        event_collection='pageviews',
        timeframe='this_7_days',
        group_by='node.id',
        filters=[
            {
                'property_name': 'node.id',
                'operator': 'exists',
                'property_value': True
            }
        ]
    )

    node_visits = client.count_unique(
        event_collection='pageviews',
        target_property='anon.id',
        timeframe='this_7_days',
        group_by='node.id',
        filters=[
            {
                'property_name': 'node.id',
                'operator': 'exists',
                'property_value': True
            }
        ]
    )

    return {'node_pageviews': node_pageviews, 'node_visits': node_visits}


def activity():
    """Generate analytics for most popular public projects and registrations.
    Called by `scripts/update_populate_projects_and_registrations`
    """
    Node = apps.get_model('osf.AbstractNode')
    popular_public_projects = []
    popular_public_registrations = []
    max_projects_to_display = settings.MAX_POPULAR_PROJECTS

    if settings.KEEN['public']['read_key']:
        keen_activity = get_keen_activity()
        node_visits = keen_activity['node_visits']

        node_data = [{'node': x['node.id'], 'views': x['result']} for x in node_visits]
        node_data.sort(key=lambda datum: datum['views'], reverse=True)

        node_data = [node_dict['node'] for node_dict in node_data]

        for nid in node_data:
            node = Node.load(nid)
            if node is None:
                continue
            if node.is_public and not node.is_registration and not node.is_deleted:
                if len(popular_public_projects) < max_projects_to_display:
                    popular_public_projects.append(node)
            elif node.is_public and node.is_registration and not node.is_deleted and not node.is_retracted:
                if len(popular_public_registrations) < max_projects_to_display:
                    popular_public_registrations.append(node)
            if len(popular_public_projects) >= max_projects_to_display and len(popular_public_registrations) >= max_projects_to_display:
                break

    # New and Noteworthy projects are updated manually
    new_and_noteworthy_pointers = Node.find_one(Q('_id', 'eq', settings.NEW_AND_NOTEWORTHY_LINKS_NODE)).nodes_pointer
    new_and_noteworthy_projects = [pointer.node for pointer in new_and_noteworthy_pointers]

    return {
        'new_and_noteworthy_projects': new_and_noteworthy_projects,
        'recent_public_registrations': recent_public_registrations(),
        'popular_public_projects': popular_public_projects,
        'popular_public_registrations': popular_public_registrations
    }
