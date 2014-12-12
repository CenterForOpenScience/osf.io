#!/usr/bin/env python
# encoding: utf-8

import os
import datetime

import tabulate
from modularodm import Q
from dateutil.relativedelta import relativedelta

from framework.analytics import get_basic_counters

from website import settings
from website.app import init_app
from website.models import User, PrivateLink
from website.addons.dropbox.model import DropboxUserSettings
from website.addons.osfstorage.model import OsfStorageFileRecord

from scripts.analytics import profile, tabulate_emails, tabulate_logs


def get_active_users():
    return User.find(
        Q('is_registered', 'eq', True) &
        Q('password', 'ne', None) &
        Q('is_merged', 'ne', True) &
        Q('date_confirmed', 'ne', None)
    )


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
    for record in OsfStorageFileRecord.find():
        page = ':'.join(['download', record.node._id, record.path])
        unique, total = get_basic_counters(page)
        downloads_unique += unique or 0
        downloads_total += total or 0
    return downloads_unique, downloads_total


def main():
    active_users = get_active_users()
    dropbox_metrics = get_dropbox_metrics()
    extended_profile_counts = profile.get_profile_counts()
    private_links = get_private_links()

    node_counts = count_user_nodes(active_users)
    nodes_at_least_1 = count_at_least(node_counts, 1)
    nodes_at_least_3 = count_at_least(node_counts, 3)

    log_counts = count_users_logs(active_users)
    logs_at_least_1 = count_at_least(log_counts, 1)
    logs_at_least_11 = count_at_least(log_counts, 11)

    log_counts_3months = count_users_logs(
        active_users,
        Q('date', 'gte', datetime.datetime.now() - relativedelta(months=3)),
    )
    logs_at_least_1_3months = count_at_least(log_counts_3months, 1)
    logs_at_least_11_3months = count_at_least(log_counts_3months, 11)

    downloads_unique, downloads_total = count_file_downloads()

    table = tabulate.tabulate(
        [
            ['active-users', active_users.count()],
            ['dropbox-users-enabled', len(dropbox_metrics['enabled'])],
            ['dropbox-users-authorized', len(dropbox_metrics['authorized'])],
            ['dropbox-users-linked', len(dropbox_metrics['linked'])],
            ['profile-edits', extended_profile_counts['any']],
            ['view-only-links', private_links.count()],
            ['nodes-gte-1', nodes_at_least_1],
            ['nodes-gte-3', nodes_at_least_3],
            ['logs-gte-1', logs_at_least_1],
            ['logs-gte-11', logs_at_least_11],
            ['logs-gte-1-last-3m', logs_at_least_1_3months],
            ['logs-gte-11-last-3m', logs_at_least_11_3months],
            ['downloads-unique', downloads_unique],
            ['downloads-total', downloads_total],
        ],
        headers=['label', 'value']
    )

    with open(os.path.join(settings.ANALYTICS_PATH, 'main.txt'), 'w') as fp:
        fp.write(table)

    tabulate_emails.main()
    tabulate_logs.main()


if __name__ == '__main__':
    init_app()
    main()
