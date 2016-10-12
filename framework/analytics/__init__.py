#!/usr/bin/env python
# encoding: utf-8

import logging
import functools
from datetime import datetime

from dateutil import parser

from framework.mongo import database
from framework.postcommit_tasks.handlers import run_postcommit
from framework.sessions import session
from framework.celery_tasks import app
from osf.models import UserActivityCounter
from website import settings

from flask import request

logger = logging.getLogger(__name__)

# TODO Find out why this is here and fix it.
collection = None
# if database._get_current_object() is not None:
#     collection = database['pagecounters']
# elif database._get_current_object() is None and settings.DEBUG_MODE:
#     logger.warn('Cannot connect to database. Analytics will be unavailable')
# else:
#     raise RuntimeError('Cannot connect to database')

@run_postcommit(once_per_request=False, celery=True)
@app.task(max_retries=5, default_retry_delay=60)
def increment_user_activity_counters(user_id, action, date_string, db=None):
    # NOTE maybe this should act differently in DEBUG_MODE, I disagree
    return UserActivityCounter.increment(user_id, action, date_string)


def get_total_activity_count(user_id, db=None):
    return UserActivityCounter.get_total_activity_count(user_id)


def clean_page(page):
    return page.replace(
        '.', '_'
    ).replace(
        '$', '_'
    )


def build_page(rex, kwargs):
    """Build page key from format pattern and request data.

    :param str: Format string (e.g. `'{node}:{file}'`)
    :param dict kwargs: Data used to render format string
    """
    target_node = kwargs.get('node') or kwargs.get('project')
    target_id = target_node._id
    data = {
        'target_id': target_id,
    }
    data.update(kwargs)
    data.update(request.args.to_dict())
    try:
        return rex.format(**data)
    except KeyError:
        return None

def update_counter(page, node_info=None, db=None):
    """Update counters for page.

    :param str page: Colon-delimited page key in analytics collection
    :param db: MongoDB database or `None`
    """
    db = db or database
    if not db and settings.DEBUG_MODE:
        logger.warn('Cannot connect to database. Analytics will be unavailable')
        return
    collection = db['pagecounters']

    date = datetime.utcnow()
    date = date.strftime('%Y/%m/%d')

    page = clean_page(page)

    d = {'$inc': {}}

    visited_by_date = session.data.get('visited_by_date')
    if not visited_by_date:
        visited_by_date = {'date': date, 'pages': []}

    if date == visited_by_date['date']:
        if page not in visited_by_date['pages']:
            d['$inc']['date.%s.unique' % date] = 1
            visited_by_date['pages'].append(page)
            session.data['visited_by_date'] = visited_by_date
    else:
        visited_by_date['date'] = date
        visited_by_date['pages'] = []
        d['$inc']['date.%s.unique' % date] = 1
        visited_by_date['pages'].append(page)
        session.data['visited_by_date'] = visited_by_date

    d['$inc']['date.%s.total' % date] = 1

    visited = session.data.get('visited')  # '/project/x/, project/y/'
    if not visited:
        visited = []
    if page not in visited:
        d['$inc']['unique'] = 1
        visited.append(page)
        session.data['visited'] = visited
    d['$inc']['total'] = 1

    # If a download counter is being updated, only perform the update
    # if the user who is downloading isn't a contributor to the project
    page_type = page.split(':')[0]
    if page_type == 'download' and node_info:
        contributors = node_info['contributors']
        current_user = session.data.get('auth_user_id')
        if current_user and current_user in contributors:
            d['$inc']['unique'] = 0
            d['$inc']['total'] = 0

    collection.update({'_id': page}, d, True, False)

def update_counters(rex, node_info=None, db=None):
    """Create a decorator that updates analytics in `pagecounters` when the
    decorated function is called. Note: call inner function before incrementing
    counters so that counters are not changed if inner function fails.

    :param rex: Pattern for building page key from keyword arguments of
        decorated function
    """
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            ret = func(*args, **kwargs)
            page = build_page(rex, kwargs)
            update_counter(page, node_info, db)
            return ret
        return wrapped
    return wrapper


def get_basic_counters(page, db=None):
    db = db or database
    if not db and settings.DEBUG_MODE:
        logger.warn('Cannot connect to database. Analytics will be unavailable')
        return
    collection = db['pagecounters']
    unique = 0
    total = 0
    collection = database['pagecounters']
    result = collection.find_one(
        {'_id': clean_page(page)},
        {'total': 1, 'unique': 1}
    )
    if result:
        if 'unique' in result:
            unique = result['unique']
        if 'total' in result:
            total = result['total']
        return unique, total
    else:
        return None, None
