# -*- coding: utf-8 -*-

import os

import tabulate
from modularodm import Q

from website import settings
from website.models import User, PrivateLink
from website.addons.dropbox.model import DropboxUserSettings

from scripts.analytics import profile


def get_active_users():
    return User.find(
        Q('is_registered', 'eq', True) &
        Q('password', 'ne', None) &
        Q('is_merged', 'ne', True) &
        Q('date_confirmed', 'ne', None)
    )


def get_dropbox_users():
    return [
        each.owner for each in DropboxUserSettings.find()
        if each.nodes_authorized
    ]


def get_private_links():
    return PrivateLink.find(
        Q('is_deleted', 'ne', True)
    )


def count_user_nodes(users=None):
    users = users or get_active_users()
    return [
        len(user.node__contributed)
        for user in users
    ]


def count_user_logs(users=None):
    users = users or get_active_users()
    return [
        len(user.nodelog__created)
        for user in users
    ]


def count_at_least(counts, at_least):
    return len([
        count for count in counts
        if count >= at_least
    ])


def main():
    active_users = get_active_users()
    dropbox_users = get_dropbox_users()
    extended_profile_counts = profile.get_profile_counts()
    private_links = get_private_links()

    node_counts = count_user_nodes(active_users)
    nodes_at_least_1 = count_at_least(node_counts, 1)
    nodes_at_least_3 = count_at_least(node_counts, 3)

    log_counts = count_user_logs(active_users)
    logs_at_least_1 = count_at_least(log_counts, 1)
    logs_at_least_11 = count_at_least(log_counts, 11)

    table = tabulate.tabulate(
        [
            ['active-users', active_users.count()],
            ['dropbox-users', len(dropbox_users)],
            ['profile-edits', extended_profile_counts['any']],
            ['view-only-links', private_links.count()],
            ['nodes-gte-1', nodes_at_least_1],
            ['nodes-gte-3', nodes_at_least_3],
            ['logs-gte-1', logs_at_least_1],
            ['logs-gte-11', logs_at_least_11],
        ],
        headers=['label', 'value']
    )

    with open(os.path.join(settings.ANALYTICS_PATH, 'main.txt'), 'w') as fp:
        fp.write(table)


if __name__ == '__main__':
    main()

