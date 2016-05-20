#!/usr/bin/env python
# encoding: utf-8

import os
import datetime
import collections

import tabulate
from modularodm import Q
from dateutil.relativedelta import relativedelta

from framework.analytics import get_basic_counters
from framework.mongo.utils import paginated

from website import settings
from website.app import init_app
from website.files.models import OsfStorageFile
from website.files.models import StoredFileNode, TrashedFileNode
from website.models import User, Node, PrivateLink, NodeLog
from website.project.utils import CONTENT_NODE_QUERY
from website.addons.dropbox.model import DropboxUserSettings

from scripts.analytics import profile, tabulate_emails, tabulate_logs


def get_active_users(extra=None):
    query = (
        Q('is_registered', 'eq', True) &
        Q('password', 'ne', None) &
        Q('merged_by', 'eq', None) &
        Q('date_confirmed', 'ne', None) &
        Q('date_disabled', ' eq', None)
    )
    query = query & extra if extra else query
    return User.find(query)


def get_dropbox_metrics():
    queryset = DropboxUserSettings.find(Q('deleted', 'eq', False))
    num_enabled = 0     # of users w/ 1+ DB account connected
    num_authorized = 0  # of users w/ 1+ DB account connected to 1+ node
    num_linked = 0      # of users w/ 1+ DB account connected to 1+ node w/ a folder linked
    for user_settings in queryset:
        if user_settings.has_auth:
            num_enabled += 1
            node_settings_list = [Node.load(guid).get_addon('dropbox') for guid in user_settings.oauth_grants.keys()]
            if any([ns.has_auth for ns in node_settings_list if ns]):
                num_authorized += 1
                if any([(ns.complete and ns.folder) for ns in node_settings_list if ns]):
                    num_linked += 1
    return {
        'enabled': num_enabled,
        'authorized': num_authorized,
        'linked': num_linked
    }


def get_private_links():
    return PrivateLink.find(
        Q('is_deleted', 'ne', True)
    )


def get_folders():
    return Node.find(
        Q('is_collection', 'eq', True) &
        Q('is_bookmark_collection', 'ne', True) &
        Q('is_deleted', 'ne', True)
    )


def count_user_nodes(users=None):
    users = users or get_active_users()
    return [
        Node.find_for_user(
            user,
            subquery=CONTENT_NODE_QUERY
        ).count()
        for user in users
        ]


def count_user_logs(user, query=None):
    if query:
        query &= Q('user', 'eq', user._id)
    else:
        query = Q('user', 'eq', user._id)
    return NodeLog.find(query).count()


def count_users_logs(users=None, query=None):
    users = users or get_active_users()
    return [
        count_user_logs(user, query)
        for user in users
    ]


def count_at_least(counts, at_least):
    return len([
        count for count in counts
        if count >= at_least
    ])


def count_file_downloads():
    downloads_unique, downloads_total = 0, 0
    for record in paginated(OsfStorageFile):
        page = ':'.join(['download', record.node._id, record._id])
        unique, total = get_basic_counters(page)
        downloads_unique += unique or 0
        downloads_total += total or 0
        clear_modm_cache()
    return downloads_unique, downloads_total


LogCounter = collections.namedtuple('LogCounter', ['label', 'delta'])

log_counters = [
    LogCounter('total', None),
    LogCounter('last-3m', relativedelta(months=3)),
    LogCounter('last-1m', relativedelta(months=1)),
    LogCounter('last-1w', relativedelta(weeks=1)),
    LogCounter('last-1d', relativedelta(days=1)),
]

log_thresholds = [1, 11]


def get_log_counts(users):
    rows = []
    for counter in log_counters:
        counts = count_users_logs(
            users,
            (
                Q('date', 'gte', datetime.datetime.utcnow() - counter.delta)
                if counter.delta
                else None
            ),
        )
        for threshold in log_thresholds:
            thresholded = count_at_least(counts, threshold)
            rows.append([
                'logs-gte-{0}-{1}'.format(threshold, counter.label),
                thresholded,
            ])
    return rows


def get_projects():
    # This count includes projects, forks, and registrations
    projects = Node.find(
        Q('parent_node', 'eq', None) &
        CONTENT_NODE_QUERY
    )
    return projects

def get_projects_forked():
    projects_forked = Node.find(
        Q('parent_node', 'eq', None) &
        Q('is_fork', 'eq', True) &
        CONTENT_NODE_QUERY
    )
    return projects_forked

def get_projects_registered():
    projects_registered = Node.find(
        Q('parent_node', 'eq', None) &
        Q('is_registration', 'eq', True) &
        CONTENT_NODE_QUERY
    )
    return projects_registered

def get_projects_public():
    projects_public = Node.find(
        Q('parent_node', 'eq', None) &
        Q('is_public', 'eq', True) &
        CONTENT_NODE_QUERY
    )
    return projects_public


def get_number_downloads_unique_and_total(projects=None):
    number_downloads_unique = 0
    number_downloads_total = 0

    projects = projects or get_projects()

    for project in projects:
        for filenode in OsfStorageFile.find(Q('node', 'eq', project)):
            for idx, version in enumerate(filenode.versions):
                page = ':'.join(['download', project._id, filenode._id, str(idx)])
                unique, total = get_basic_counters(page)
                number_downloads_unique += unique or 0
                number_downloads_total += total or 0

        for filenode in TrashedFileNode.find(Q('provider', 'eq', 'osfstorage') & Q('node', 'eq', project) & Q('is_file', 'eq', True)):
            for idx, version in enumerate(filenode.versions):
                page = ':'.join(['download', project._id, filenode._id, str(idx)])
                unique, total = get_basic_counters(page)
                number_downloads_total += total or 0
                number_downloads_unique += unique or 0

        clear_modm_cache()

    return number_downloads_unique, number_downloads_total


def clear_modm_cache():
    StoredFileNode._cache.data.clear()
    StoredFileNode._object_cache.data.clear()
    TrashedFileNode._cache.data.clear()
    TrashedFileNode._object_cache.data.clear()
    Node._cache.data.clear()
    Node._object_cache.data.clear()


def main():

    number_users = User.find().count()
    projects = get_projects()
    projects_forked = get_projects_forked()
    projects_registered = get_projects_registered()

    number_projects = projects.count()

    projects_public = get_projects_public()
    number_projects_public = projects_public.count()
    number_projects_forked = projects_forked.count()

    number_projects_registered = projects_registered.count()

    number_downloads_unique, number_downloads_total = get_number_downloads_unique_and_total(projects=projects)

    active_users = get_active_users()
    active_users_invited = get_active_users(Q('is_invited', 'eq', True))
    dropbox_metrics = get_dropbox_metrics()
    extended_profile_counts = profile.get_profile_counts()
    private_links = get_private_links()
    folders = get_folders()
    downloads_unique, downloads_total = count_file_downloads()

    node_counts = count_user_nodes(active_users)
    nodes_at_least_1 = count_at_least(node_counts, 1)
    nodes_at_least_3 = count_at_least(node_counts, 3)

    rows = [
        ['number_users', number_users],
        ['number_projects', number_projects],
        ['number_projects_public', number_projects_public],
        ['number_projects_forked', number_projects_forked],
        ['number_projects_registered', number_projects_registered],
        ['number_downloads_total', number_downloads_total],
        ['number_downloads_unique', number_downloads_unique],
        ['active-users', active_users.count()],
        ['active-users-invited', active_users_invited.count()],
        ['dropbox-users-enabled', dropbox_metrics['enabled']],
        ['dropbox-users-authorized', dropbox_metrics['authorized']],
        ['dropbox-users-linked', dropbox_metrics['linked']],
        ['profile-edits', extended_profile_counts['any']],
        ['view-only-links', private_links.count()],
        ['folders', folders.count()],
        ['downloads-unique', downloads_unique],
        ['downloads-total', downloads_total],
        ['nodes-gte-1', nodes_at_least_1],
        ['nodes-gte-3', nodes_at_least_3],
    ]

    rows.extend(get_log_counts(active_users))

    table = tabulate.tabulate(
        rows,
        headers=['label', 'value'],
    )

    with open(os.path.join(settings.ANALYTICS_PATH, 'main.txt'), 'w') as fp:
        fp.write(table)

    tabulate_emails.main()
    tabulate_logs.main()


if __name__ == '__main__':
    init_app()
    main()
