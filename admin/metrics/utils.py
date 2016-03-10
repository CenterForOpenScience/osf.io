"""
Metrics scripts
"""
from datetime import datetime, timedelta
from modularodm import Q
from website.project.model import User, Node

from .models import OSFStatistic


def osf_site():
    current_time = datetime.utcnow()
    latest = None
    if OSFStatistic.objects.count() != 0:
        latest = OSFStatistic.objects.latest('date')
        if latest.date.date() == current_time.date():
            return  # Don't add another
    midnight = current_time - timedelta(
        hours=current_time.hour,
        minutes=current_time.minute
    )
    statistic = OSFStatistic(date=current_time)
    query = Q('date_registered', 'lt', midnight)
    statistic.users = User.find(query).count()
    statistic.projects = get_projects(time=midnight)
    statistic.public_projects = get_projects(time=midnight, public=True)
    statistic.registered_projects = get_projects(time=midnight, registered=True)
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
    projects = Node.find(query)
    return len(projects)
