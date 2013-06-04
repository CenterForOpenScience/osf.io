import Framework
from Framework.Analytics import db as analytics

from Site.Project import Node
from pymongo import DESCENDING


@Framework.get('/discover/')
def discover():
    recent_public = Node.storage.db.find(
        {
            'category': 'project',
            'is_public': True,
            'is_deleted': False,
        }
    ).sort(
        'date_created',
        direction=DESCENDING
    )[:10]

    most_viewed_by_id = analytics['pagecounters'].find(
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
        node_id = next(most_viewed_by_id)['_id']
        node = Node.load(node_id.split(':')[1])
        if (
            node.is_public and
            node.category == 'project' and
            (not node.is_deleted)
        ):
            most_viewed_projects.append(node)

    return Framework.render(
        'discover.mako',
        recent_public=[Node.load(x['_id']) for x in recent_public],
        most_viewed=most_viewed_projects
    )