"""
Metrics scripts
"""
from datetime import datetime, timedelta
from modularodm import Q
from website.project.model import User, Node
from website.project.utils import CONTENT_NODE_QUERY


from .models import OSFWebsiteStatistics

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
    if OSFWebsiteStatistics.objects.count() != 0:
        latest = OSFWebsiteStatistics.objects.latest('date')
        if latest.date.date() == time.date():
            return  # Don't add another
        dates = get_list_of_dates(latest.date, time)
    else:
        dates = [time]
    for date in dates:
        get_days_statistics(date, latest)
        latest = OSFWebsiteStatistics.objects.latest('date')


def get_days_statistics(time, latest=None):
    statistics = OSFWebsiteStatistics(date=time)
    # Basic user count
    statistics.users = get_active_user_count(time)
    # Users who are currently unregistered
    statistics.unregistered_users = get_unregistered_users()
    statistics.projects = get_projects(time=time)
    statistics.public_projects = get_projects(time=time, public=True)
    statistics.registered_projects = get_projects(time=time, registered=True)
    if latest:
        statistics.delta_users = statistics.users - latest.users
        statistics.delta_projects = statistics.projects - latest.projects
        statistics.delta_public_projects = statistics.public_projects - latest.public_projects
        statistics.delta_registered_projects = statistics.registered_projects - latest.registered_projects
    statistics.save()


def get_projects(time=None, public=False, registered=False):
    query = (
        Q('parent_node', 'eq', None) &
        CONTENT_NODE_QUERY
    )
    if time:
        query = query & Q('date_created', 'lt', time)
    if public:
        query = query & Q('is_public', 'eq', True)
    if registered:
        query = query & Q('is_registration', 'eq', True)
    return Node.find(query).count()


def get_active_user_count(time):
    query = (
        Q('date_registered', 'lt', time) &
        Q('is_registered', 'eq', True) &
        Q('password', 'ne', None) &
        Q('merged_by', 'eq', None) &
        Q('date_confirmed', 'ne', None) &
        Q('date_disabled', ' eq', None)
    )
    return User.find(query).count()


def get_unregistered_users():
    query = (
        Q('is_registered', 'eq', False)
    )
    return User.find(query).count()
