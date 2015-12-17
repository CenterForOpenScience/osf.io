import csv
import datetime
import tabulate
import sys
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
    users = get_active_users(Q('username', 'eq', email))
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


def find_user_by_lastname(family_name):
    users = get_active_users(Q('family_name', 'eq', family_name))
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
    return node_logs[node_logs.count()-1].date


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
            username = row['Email Address']
            full_name = row['Name']
            family_name = impute_names(full_name)['family']
            parsed_date = row['Workshop_Date'].split("/")
            day, month, year = int(parsed_date[0]), int(parsed_date[1]), int('20'+parsed_date[2])
            date = datetime.datetime(year, month, day)

            found_user = find_user_by_email(username) or find_user_by_fullname(full_name) or find_user_by_lastname(family_name)
            if found_user:
                log_count = count_user_logs(found_user, Q('date', 'gte', date))
                node_count = count_user_nodes(found_user, Q('date_created', 'gte', date))
                last_log = user_last_log(found_user)
                rows.add((date, found_user.fullname, found_user.username, found_user._id, log_count, node_count, last_log))
    return rows



def main():
    csvfile = sys.argv[0]
    rows = get_users_from_csv(csvfile)
    table = tabulate.tabulate(
        (sorted(rows, key=lambda row: row[0], reverse=True)),
        headers=['Date of Workshop', 'Fullname', 'Email', 'GUID', 'Logs Since Workshop', 'Nodes Since Workshop', 'Last Log Date'],
    )
    print(table.encode('utf8'))

if __name__ == '__main__':
    init_app()
    main()
