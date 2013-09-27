from framework import db, session

from decorator import decorator
from datetime import datetime
import re

collectionName = 'pagecounters'
collection = db[collectionName]


def increment_user_activity_counters(user_id, action, date):
    collectionName = 'useractivitycounters'
    collection = db[collectionName]
    date = date.strftime('%Y/%m/%d') # todo remove slashes
    d = {'$inc': {}}
    d['$inc']['total'] = 1
    d['$inc']['date.{0}.total'.format(date)] = 1
    d['$inc']['action.{0}.total'.format(action)] = 1
    d['$inc']['action.{0}.date.{1}'.format(action, date)] = 1
    collection.update({'_id': user_id}, d, True, False)
    return True


def get_total_activity_count(user_id):
    collectionName = 'useractivitycounters'
    collection = db[collectionName]
    result = collection.find_one(
        {'_id': user_id}, {'total': 1}
    )
    if result and 'total' in result:
        return result['total']
    return None


def update_counters(rex):
    def wrapped(func, *args, **kwargs):
        date = datetime.utcnow()
        date = date.strftime('%Y/%m/%d')
        #path = request.path
        try:
            page = rex.format(**kwargs).replace('.',
                                                '_') #re.search(rex, path).group(0)
        except KeyError:
            return func(*args, **kwargs)

        d = {'$inc': {}}

        visitedByDate = session.data.get('visited_by_date')
        if not visitedByDate:
            visitedByDate = {'date': date, 'pages': []}

        if date == visitedByDate['date']:
            if page not in visitedByDate['pages']:
                d['$inc']['date.%s.unique' % date] = 1
                visitedByDate['pages'].append(page)
                session.data['visited_by_date'] = visitedByDate
        else:
            visitedByDate['date'] = date
            visitedByDate['pages'] = []
            d['$inc']['date.%s.unique' % date] = 1
            visitedByDate['pages'].append(page)
            session.data['visited_by_date'] = visitedByDate

        d['$inc']['date.%s.total' % date] = 1

        visited = session.data.get('visited') # '/project/x/, project/y/'
        if not visited:
            visited = []
        if page not in visited:
            d['$inc']['unique'] = 1
            visited.append(page)
            session.data['visited'] = visited
        d['$inc']['total'] = 1
        collection.update({'_id': page}, d, True, False)
        return func(*args, **kwargs)

    return decorator(wrapped)


def get_basic_counters(page):
    unique = 0
    total = 0
    result = collection.find_one(
        {'_id': page}, {'total': 1, 'unique': 1}
    )
    if result:
        if 'unique' in result:
            unique = result['unique']
        if 'total' in result:
            total = result['total']
        return (unique, total)
    else:
        return (None, None)


def get_days_counters(page):
    result = collection.find_one(
        {'_id': page}, {'date': 1}
    )
    dates = []
    unique = []
    total = []
    if 'date' in result:
        for k, v in result['date'].items():
            dates.append(k)
            u = 0
            t = 0
            if 'unique' in v:
                u = v['unique']
            if 'total' in v:
                t = v['total']

            unique.append(u)
            total.append(t)
    else:
        return None
    return {'dates': dates, 'unique': unique, 'total': total}


def get_day_total_list(page):
    result = collection.find_one(
        {'_id': page}, {'date': 1}
    )
    dates = {}
    if 'date' in result:
        for k, v in result['date'].items():
            dates[k] = 0
            if 'total' in v:
                dates[k] = v['total']
        sorted_dates = sorted(dates.keys())
        return zip(sorted_dates, map(dates.get, sorted_dates))
    else:
        return None
