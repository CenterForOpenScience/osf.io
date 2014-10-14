from website import settings
from website.project import Node

from modularodm.query.querydialect import DefaultQueryDialect as Q

from framework.analytics.piwik import PiwikClient

def activity():

    popular_public_projects = []
    popular_public_registrations = []
    hits = {}

    if settings.PIWIK_HOST:
        client = PiwikClient(
            url=settings.PIWIK_HOST,
            auth_token=settings.PIWIK_ADMIN_TOKEN,
            site_id=settings.PIWIK_SITE_ID,
            period='week',
            date='today',
        )
        popular_project_ids = [
            x for x in client.custom_variables if x.label == 'Project ID'
        ][0].values

        for nid in popular_project_ids:
            node = Node.load(nid.value)
            if node is None:
                continue
            if node.is_public and not node.is_registration:
                if len(popular_public_projects) < 10:
                    popular_public_projects.append(node)
            elif node.is_public and node.is_registration:
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

    # Registrations
    recent_public_registrations = Node.find(
        recent_query &
        Q('is_registration', 'eq', True)
    ).sort(
        '-registered_date'
    ).limit(10)

    return {
        'recent_public_projects': recent_public_projects,
        'recent_public_registrations': recent_public_registrations,
        'popular_public_projects': popular_public_projects,
        'popular_public_registrations': popular_public_registrations,
        'hits': hits,
    }
