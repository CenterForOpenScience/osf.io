# -*- coding: utf-8 -*-
import functools
from datetime import datetime

from framework.mongo import database
from framework.sessions import session


collection = database['pagecounters']

def increment_user_activity_counters(user_id, action, date, db=None):
    db = db or database  # default to local proxy
    collection = database['useractivitycounters']
    date = date.strftime('%Y/%m/%d')
    query = {
        '$inc': {
            'total': 1,
            'date.{0}.total'.format(date): 1,
            'action.{0}.total'.format(action): 1,
            'action.{0}.date.{1}'.format(action, date): 1,
        }
    }
    collection.update(
        {'_id': user_id},
        query,
        upsert=True,
        manipulate=False,
    )
    return True


def get_total_activity_count(user_id, db=None):
    db = db or database
    collection = database['useractivitycounters']
    result = collection.find_one(
        {'_id': user_id}, {'total': 1}
    )
    if result and 'total' in result:
        return result['total']
    return 0


def update_counters(rex, db=None):
    """
    Create a decorator that updates analytics in `pagecounters` when the decorated
    function is called.

    :param rex: Pattern for building page key from keyword arguments of decorated function

    """
    db = db or database

    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            date = datetime.utcnow()
            date = date.strftime('%Y/%m/%d')
            target_node = kwargs.get('node') or kwargs.get('project')
            target_id = target_node._id
            data = {
                'target_id': target_id,
            }
            data.update(kwargs)
            try:
                page = rex.format(**data).replace('.', '_')
            except KeyError:
                return func(*args, **kwargs)

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
            collection = database['pagecounters']
            collection.update({'_id': page}, d, True, False)
            return func(*args, **kwargs)
        return wrapped
    return wrapper


def get_basic_counters(page, db=None):
    db = db or database
    collection = db['pagecounters']
    unique = 0
    total = 0
    collection = database['pagecounters']
    result = collection.find_one(
        {'_id': page}, {'total': 1, 'unique': 1}
    )
    if result:
        if 'unique' in result:
            unique = result['unique']
        if 'total' in result:
            total = result['total']
        return unique, total
    else:
        return None, None
