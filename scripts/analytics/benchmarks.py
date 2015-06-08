#!/usr/bin/env python
# encoding: utf-8

import os
import datetime
import collections

import tabulate
from modularodm import Q
from dateutil.relativedelta import relativedelta

from framework.analytics import get_basic_counters

from website import settings
from website.app import init_app
from website.models import User, Node, PrivateLink
from website.addons.dropbox.model import DropboxUserSettings
from website.addons.osfstorage.model import OsfStorageFileNode
from website.addons.osfstorage.model import OsfStorageTrashedFileNode

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
    metrics = {
        'enabled': [],
        'authorized': [],
        'linked': [],
    }
    for node_settings in DropboxUserSettings.find():
        metrics['enabled'].append(node_settings)
        if node_settings.has_auth:
            metrics['authorized'].append(node_settings)
        if node_settings.nodes_authorized:
            metrics['linked'].append(node_settings)
    return metrics


def get_private_links():
    return PrivateLink.find(
        Q('is_deleted', 'ne', True)
    )


def get_folders():
    return Node.find(
        Q('is_folder', 'eq', True) &
        Q('is_dashboard', 'ne', True) &
        Q('is_deleted', 'ne', True)
    )


def count_user_nodes(users=None):
    users = users or get_active_users()
    return [
        len(
            user.node__contributed.find(
                Q('is_deleted', 'eq', False) &
                Q('is_folder', 'ne', True)
            )
        )
        for user in users
    ]


def count_user_logs(user, query=None):
    if query:
        return len(user.nodelog__created.find(query))
    return len(user.nodelog__created)


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
    for record in OsfStorageFileNode.find():
        page = ':'.join(['download', record.node._id, record._id])
        unique, total = get_basic_counters(page)
        downloads_unique += unique or 0
        downloads_total += total or 0
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
    projects = Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True)
    )

def get_projects_forked():
    projects_forked = list(Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True) &
        Q('is_fork', 'eq', True)
    ))

def get_projects_registered():
    projects_registered = Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True) &
        Q('is_registration', 'eq', True)
    )


def main():

    number_users = User.find().count()
    projects = get_projects()
    projects_forked = get_projects_forked()
    projects_registered = get_projects_registered()

    pf = []
    for p in projects_forked:
        if not p.contributors[0]:
            continue
        name = p.contributors[0].fullname
        if unicode(name) not in [u'Jeffres R. Spies', 'Brian A. Nosek']:
            pf.append(p)

    pr = []
    for p in projects_registered:
        name = p.contributors[0].fullname
        if not p.contributors[0]:
            continue
        if not unicode(name)==u'Jeffrey R. Spies' and not unicode(name)==u'Brian A. Nosek':
            pr.append(p)

    number_projects = len(projects)
    number_projects_public = Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True) &
        Q('is_public', 'eq', True)
    ).count()
    number_projects_forked = len(pf)

    number_projects_registered = len(pr)

    ##############

    number_downloads_total = 0
    number_downloads_unique = 0

    contributors_per_project = []

    contrib = {}

    for project in projects:
        contributors_per_project.append(len(project.contributors))
        for person in project.contributors:
            if not person:
                continue
            if person._id not in contrib:
                contrib[person._id] = []
            for neighbor in project.contributors:
                if not neighbor:
                    continue
                if neighbor._id not in contrib[person._id]:
                    contrib[person._id].append(neighbor._id)

        addon = project.get_addon('osfstorage')

        for filenode in OsfStorageFileNode.find(Q('node_settings', 'eq', addon) & Q('kind', 'eq', 'file')):
            for idx, version in enumerate(filenode.versions):
                page = ':'.join(['download', project._id, filenode._id, str(idx)])
                unique, total = get_basic_counters(page)
                number_downloads_total += total or 0
                number_downloads_unique += unique or 0

        for filenode in OsfStorageTrashedFileNode.find(Q('node_settings', 'eq', addon) & Q('kind', 'eq', 'file')):
            for idx, version in enumerate(filenode.versions):
                page = ':'.join(['download', project._id, filenode._id, str(idx)])
                unique, total = get_basic_counters(page)
                number_downloads_total += total or 0
                number_downloads_unique += unique or 0


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
        ['dropbox-users-enabled', len(dropbox_metrics['enabled'])],
        ['dropbox-users-authorized', len(dropbox_metrics['authorized'])],
        ['dropbox-users-linked', len(dropbox_metrics['linked'])],
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
