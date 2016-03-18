"""
Metrics scripts
"""
from datetime import datetime, timedelta
from modularodm import Q
from website.project.model import User, Node

from .models import OSFStatistic

DAY_LEEWAY = 86400 - 60  # How many seconds are counted as a full day for the
# last day


def get_list_of_dates(start, end):
    delta = end - start
    if delta.seconds > DAY_LEEWAY:
        delta = delta + timedelta(hours=1)
    return [start + (s * timedelta(days=1)) for s in xrange(1, delta.days + 1)]


def get_previous_midnight(time=None):
    if time is None:
        time = datetime.utcnow()
    return time - timedelta(  # As close to midnight utc as possible
        hours=time.hour,
        minutes=time.minute,
        seconds=time.second,
        microseconds=time.microsecond - 1
    )


def get_osf_statistics(time=None):
    """ get all dates since the latest

    :param time: immediately turns into the previous midnight
    :return: nothing
    """
    time = get_previous_midnight(time)
    latest = None
    if OSFStatistic.objects.count() != 0:
        latest = OSFStatistic.objects.latest('date')
        if latest.date.date() == time.date():
            return  # Don't add another
    for date in get_list_of_dates(latest.date, time):
        get_days_statistics(date, latest)
        latest = OSFStatistic.objects.latest('date')


def get_days_statistics(time, latest=None):
    statistic = OSFStatistic(date=time)
    # Basic user count
    statistic.users = get_all_user_count(time)
    # Users who are currently unregistered
    statistic.unregistered_users = get_unregistered_users()
    statistic.projects = get_projects(time=time)
    statistic.public_projects = get_projects(time=time, public=True)
    statistic.registered_projects = get_projects(time=time, registered=True)
    if latest:
        statistic.delta_users = statistic.users - latest.users
        statistic.delta_projects = statistic.projects - latest.projects
        statistic.delta_public_projects = statistic.public_projects - latest.public_projects
        statistic.delta_registered_projects = statistic.registered_projects - latest.registered_projects
    statistic.save()


def get_projects(time=None, public=False, registered=False):
    query = (
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True)
    )
    if time:
        query = query & Q('date_created', 'lt', time)
    if public:
        query = query & Q('is_public', 'eq', True)
    if registered:
        query = query & Q('is_registration', 'eq', True)
    return Node.find(query).count()


def get_all_user_count(time):
    query = Q('date_registered', 'lt', time)
    return User.find(query).count()


def get_unregistered_users():
    query = (
        Q('is_registered', 'eq', False)
    )
    return User.find(query).count()
