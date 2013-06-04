import Framework
from Framework.Analytics import db as analytics

from Site.Project import Node
from pymongo import DESCENDING


@Framework.get('/discover/')
def discover():
    # Projects

    recent_public_projects = Node.storage.db.find(
        {
            'category': 'project',
            'is_public': True,
            'is_deleted': False,
            'is_registration': False
        }
    ).sort(
        'date_created',
        direction=DESCENDING
    )[:10]

    most_viewed_project_ids = analytics['pagecounters'].find(
        {
            '_id': {
                '$regex': '^node:'
            }
        }
    ).sort(
        'total',
        direction=DESCENDING
    )

    most_viewed_projects = []
    while len(most_viewed_projects) < 10:
        node_id = next(most_viewed_project_ids)['_id']
        node = Node.load(node_id.split(':')[1])
        if (
            node.is_public and
            node.category == 'project' and
            (not node.is_deleted) and
            (not node.is_registration)
        ):
            most_viewed_projects.append(node)

    # Registrations

    recent_public_registrations = Node.storage.db.find(
        {
            'category': 'project',
            'is_public': True,
            'is_deleted': False,
            'is_registration': True
        }
    ).sort(
        'date_created',
        direction=DESCENDING
    )[:10]

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
        node_id = next(most_viewed_registration_ids)['_id']
        node = Node.load(node_id.split(':')[1])
        if (
            node.is_public and
            node.category == 'project' and
            (not node.is_deleted) and
            node.is_registration
        ):
            most_viewed_registrations.append(node)

    return Framework.render(
        'discover.mako',
        recent_public_projects=[Node.load(x['_id'])
                                for x in recent_public_projects],
        most_viewed_projects=most_viewed_projects,
        recent_public_registrations=[Node.load(x['_id'])
                                     for x in recent_public_registrations],
        most_viewed_registrations=most_viewed_registrations,
    )