import datetime

from website import settings
from website.project import Node
from website.project.utils import recent_public_registrations

from modularodm.query.querydialect import DefaultQueryDialect as Q

from framework.analytics.piwik import PiwikClient

def activity():

    popular_public_projects = []
    popular_public_registrations = []
    hits = {}

    # get the date for exactly one week ago
    target_date = datetime.date.today() - datetime.timedelta(weeks=1)

    if settings.PIWIK_HOST:
        client = PiwikClient(
            url=settings.PIWIK_HOST,
            auth_token=settings.PIWIK_ADMIN_TOKEN,
            site_id=settings.PIWIK_SITE_ID,
            period='week',
            date=target_date.strftime('%Y-%m-%d'),
        )

        popular_project_ids = [
            x for x in client.custom_variables if x.label == 'Project ID'
        ][0].values

        for nid in popular_project_ids:
            node = Node.load(nid.value)
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
            x.value: {
                'hits': x.actions,
                'visits': x.visits
            } for x in popular_project_ids
        }

    # Projects

    # Only show top-level projects (any category) in new and noteworthy lists
    # This means that public children of private nodes will be excluded
    recent_query = (
        Q('parent_node', 'eq', None) &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False) &
        Q('is_collection', 'ne', True) &
        Q('is_bookmark_collection', 'ne', True)
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
