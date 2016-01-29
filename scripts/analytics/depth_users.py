#!/usr/bin/env python
# encoding: utf-8

import tabulate
from modularodm import Q

from website.app import init_app
from website.models import User, NodeLog


LOG_THRESHOLD = 11


def get_active_users(extra=None):
    query = (
        Q('is_registered', 'eq', True) &
        Q('password', 'ne', None) &
        Q('merged_by', 'eq', None) &
        Q('date_confirmed', 'ne', None) &
        Q('date_disabled', 'eq', None)
    )
    query = query & extra if extra else query
    return User.find(query)


def count_user_logs(user, query=None):
    if query:
        query &= Q('user', 'eq', user._id)
    else:
        query = Q('user', 'eq', user._id)
    logs = NodeLog.find(query)
    length = logs.count()
    if length > 0:
        item = logs[0]
        if item.action == 'project_created' and item.node.is_dashboard:
            length -= 1
    return length


def get_depth_users(users):
    rows = []
    for user in users:
        log_count = count_user_logs(user)
        if log_count >= LOG_THRESHOLD:
            rows.append((user.fullname, user.username, log_count))
    return rows


def main():
    active_users = get_active_users()
    rows = get_depth_users(active_users)
    table = tabulate.tabulate(
        sorted(rows, key=lambda row: row[2]),
        headers=['fullname', 'email', 'logs'],
    )
    print(table.encode('utf8'))


if __name__ == '__main__':
    init_app()
    main()
