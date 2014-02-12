from framework import db as analytics

from website import settings
from website.project import Node
from pymongo import DESCENDING

from modularodm.query.querydialect import DefaultQueryDialect as Q

from framework.analytics.piwik import PiwikClient

from itertools import islice

def activity():
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

    popular_public_projects = [
        Node.load(x.value) for x in islice(
            (
                x for x in popular_project_ids
                if Node.load(x.value).is_public
                and not Node.load(x.value).is_registration
            ),
            10,
        )
    ]

    popular_public_registrations = [
        Node.load(x.value) for x in islice(
            (
                x for x in popular_project_ids
                if Node.load(x.value).is_public
                and Node.load(x.value).is_registration
            ),
            10,
        )
    ]

    hits = {x.value: {'hits': x.actions, 'visits': x.visits} for x in popular_project_ids}

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


    # Registrations
    recent_public_registrations = Node.find(
        recent_query &
        Q('is_registration', 'eq', True)
    ).sort(
        '-date_created'
    ).limit(10)

    return {
        'recent_public_projects': recent_public_projects,
        'recent_public_registrations': recent_public_registrations,
        'popular_public_projects': popular_public_projects,
        'popular_public_registrations': popular_public_registrations,
        'hits': hits,
    }
