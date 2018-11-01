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


def update_counter(page, node_info=None):
    """Update counters for page.

    :param str page: Colon-delimited page key in analytics collection
    """
    from osf.models import PageCounter
    return PageCounter.update_counter(page, node_info)
