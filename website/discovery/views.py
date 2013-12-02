import framework
from framework import db as analytics

from website.project import Node
from pymongo import DESCENDING

from modularodm.query.querydialect import DefaultQueryDialect as Q

def activity():
    # Projects

    recent_query = (
        Q('category', 'eq', 'project') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )

    # Temporary bug fix: Skip projects with empty contributor lists
    # Todo: Fix underlying bug and remove this selector
    recent_query = recent_query & Q('contributors', 'ne', [])

    recent_public_projects = Node.find(
        recent_query &
        Q('is_registration', 'eq', False)
    ).sort(
        '-date_created'
    ).limit(10)

    most_viewed_project_ids = analytics['pagecounters'].find(
        {
            '_id': {
                '$regex': '^node:'
            }
        },
        {'_id' : 1}
    ).sort(
        'total',
        direction=DESCENDING
    )

    most_viewed_projects = []
    while len(most_viewed_projects) < 10:
        try:
            node_id = next(most_viewed_project_ids)['_id']
        except StopIteration:
            break
        node = Node.load(node_id.split(':')[1])
        if (
            node and
            node.is_public and
            node.category == 'project' and
            (not node.is_deleted) and
            (not node.is_registration)
        ):
            most_viewed_projects.append(node)

    # Registrations
    recent_public_registrations = Node.find(
        recent_query &
        Q('is_registration', 'eq', True)
    ).sort(
        '-date_created'
    ).limit(10)

    most_viewed_registration_ids = analytics['pagecounters'].find(
        {
            '_id': {
                '$regex': '^node:'
            }
        }
    ).sort(
        'total',
        direction=DESCENDING
    )

    most_viewed_registrations = []
    while len(most_viewed_registrations) < 10:
        try:
            node_id = next(most_viewed_registration_ids)['_id']
        except StopIteration:
            break
        node = Node.load(node_id.split(':')[1])
        if (
            node is not None and
            node.is_public and
            node.category == 'project' and
            (not node.is_deleted) and
            node.is_registration
        ):
            most_viewed_registrations.append(node)

    return {
        'recent_public_projects': recent_public_projects,
        'most_viewed_projects': most_viewed_projects,
        'recent_public_registrations': recent_public_registrations,
        'most_viewed_registrations': most_viewed_registrations,
    }
