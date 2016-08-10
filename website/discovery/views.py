from website import settings
from website.project import Node
from website.project.utils import CONTENT_NODE_QUERY, recent_public_registrations

from keen import KeenClient

from modularodm.query.querydialect import DefaultQueryDialect as Q


def activity():

    popular_public_projects = []
    popular_public_registrations = []
    hits = {}
    max_popular_projects = 20

    if settings.KEEN['public']['read_key']:
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

        node_data = [{'node': x['node.id'], 'views': x['result']} for x in node_pageviews[0:max_popular_projects]]

        for node_visit in node_visits[0:max_popular_projects]:
            for node_result in node_data:
                if node_visit['node.id'] == node_result['node']:
                    node_result.update({'visits': node_visit['result']})

        node_data.sort(key=lambda datum: datum['views'], reverse=True)

        for nid in node_data:
            node = Node.load(nid['node'])
            if node is None:
                continue
            if node.is_public and not node.is_registration and not node.is_deleted:
                if len(popular_public_projects) < 10:
                    popular_public_projects.append(node)
            elif node.is_public and node.is_registration and not node.is_deleted and not node.is_retracted:
                if len(popular_public_registrations) < 10:
                    popular_public_registrations.append(node)
            if len(popular_public_projects) >= 10 and len(popular_public_registrations) >= 10:
                break

        hits = {
            datum['node']: {
                'hits': datum['views'],
                'visits': datum['visits']
            } for datum in node_data
        }

    # Projects

    # Only show top-level projects (any category) in new and noteworthy lists
    # This means that public children of private nodes will be excluded
    recent_query = (
        Q('parent_node', 'eq', None) &
        Q('is_public', 'eq', True) &
        CONTENT_NODE_QUERY
    )

    recent_public_projects = Node.find(
        recent_query &
        Q('is_registration', 'eq', False)
    ).sort(
        '-date_created'
    ).limit(10)

    return {
        'recent_public_projects': recent_public_projects,
        'recent_public_registrations': recent_public_registrations(),
        'popular_public_projects': popular_public_projects,
        'popular_public_registrations': popular_public_registrations,
        'hits': hits,
    }
