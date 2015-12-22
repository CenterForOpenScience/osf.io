import csv
import tabulate
import sys
from dateutil.parser import parse as parse_date

from modularodm import Q

from website.app import init_app
from website.models import User, NodeLog, Node

from framework.auth.utils import impute_names


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


def find_user_by_email(email):
    users = get_active_users(Q('emails', 'eq', email))
    if users.count() == 1:
        return users[0]
    else:
        return None


def find_user_by_fullname(fullname):
    users = get_active_users(Q('fullname', 'eq', fullname))
    if users.count() == 1:
        return users[0]
    else:
        return None


def find_user_by_names(names):
    users = get_active_users(Q('given_name', 'eq', names['given']) & Q('family_name', 'eq', names['family']))
    if users.count() == 1:
        return users[0]
    else:
        return None


def count_user_logs(user, query=None):
    if query:
        query &= Q('user', 'eq', user._id)
    else:
        query = Q('user', 'eq', user._id)
    return NodeLog.find(query).count()


def user_last_log(user, query=None):
    if query:
        query &= Q('user', 'eq', user._id)
    else:
        query = Q('user', 'eq', user._id)

    node_logs = NodeLog.find(query)
    if node_logs.count():
        return node_logs[node_logs.count()-1].date
    return None


def count_user_nodes(user, query=None):
    if query:
        query &= Q('creator', 'eq', user._id)
    else:
        query = Q('creator', 'eq', user._id)
    return Node.find(query).count()


def get_users_from_csv(filename):
    rows = set()
    with open(filename, 'rU') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            email = row['Email Address']
            full_name = row['Name'].decode('utf-8', 'ignore')
            names = impute_names(full_name)
            date = parse_date(row['Workshop_Date'])

            found_user = find_user_by_email(email)
            if not found_user and full_name:
                found_user = find_user_by_fullname(full_name) or find_user_by_names(names)

            if found_user:
                log_count = count_user_logs(found_user, Q('date', 'gte', date))
                node_count = count_user_nodes(found_user, Q('date_created', 'gte', date))
                last_log = user_last_log(found_user)
                rows.add((date, found_user.fullname, found_user.username, found_user._id, log_count, node_count, last_log))
    return rows


def main():
    csvfile = sys.argv[1]
    rows = get_users_from_csv(csvfile)
    table = tabulate.tabulate(
        (sorted(rows, key=lambda row: row[0], reverse=True)),
        headers=['Date of Workshop', 'Fullname', 'Email', 'GUID', 'Logs Since Workshop', 'Nodes Since Workshop', 'Last Log Date'],
    )
    print(table.encode('utf8'))


if __name__ == '__main__':
    init_app()
    main()
