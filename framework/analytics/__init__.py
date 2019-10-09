# encoding: utf-8

import logging

from framework.celery_tasks import app
from framework.postcommit_tasks.handlers import run_postcommit

logger = logging.getLogger(__name__)


@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def increment_user_activity_counters(user_id, action, date_string):
    from osf.models import UserActivityCounter
    return UserActivityCounter.increment(user_id, action, date_string)


def get_total_activity_count(user_id):
    from osf.models import UserActivityCounter
    return UserActivityCounter.get_total_activity_count(user_id)


def update_counter(resource, file, version, action, node_info=None):
    """Update counters for resource.

    :param obj resource
    :param obj file
    :param int version
    :param str action, ex. 'download'
    """
    from osf.models import PageCounter
    return PageCounter.update_counter(resource, file, version=version, action=action, node_info=node_info)


def get_basic_counters(resource, file, version, action):
    from osf.models import PageCounter
    return PageCounter.get_basic_counters(resource, file, version=version, action=action)
