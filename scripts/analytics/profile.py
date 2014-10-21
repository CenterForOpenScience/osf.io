# -*- coding: utf-8 -*-

import os
from tabulate import tabulate

from framework.mongo import database
from website import settings

from .utils import mkdirp


user_collection = database['user']

TAB_PATH = os.path.join(settings.ANALYTICS_PATH, 'tables', 'features')
mkdirp(TAB_PATH)


def get_profile_counts():

    users_total = user_collection.find()

    query_jobs = {'jobs': {'$nin': [None, []]}}
    query_schools = {'schools': {'$nin': [None, []]}}
    query_social = {'social': {'$nin': [None, {}]}}

    users_jobs = user_collection.find(query_jobs)
    users_schools = user_collection.find(query_schools)
    users_social = user_collection.find(query_social)

    users_any = user_collection.find({
        '$or': [
            query_jobs,
            query_schools,
            query_social,
        ]
    })

    return {
        'total': users_total.count(),
        'jobs': users_jobs.count(),
        'schools': users_schools.count(),
        'social': users_social.count(),
        'any': users_any.count(),
    }


def main():

    counts = get_profile_counts()
    keys = ['total', 'jobs', 'schools', 'social', 'any']

    table = tabulate(
        [[counts[key] for key in keys]],
        headers=keys,
    )

    with open(os.path.join(TAB_PATH, 'extended-profile.txt'), 'w') as fp:
        fp.write(table)


if __name__ == '__main__':
    main()

