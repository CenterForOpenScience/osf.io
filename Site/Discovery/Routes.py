import Framework
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



    return Framework.render(
        'discover.mako',
        recent_public=[Node.load(x['_id']) for x in recent_public]
    )