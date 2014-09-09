# -*- coding: utf-8 -*-

import os
from tabulate import tabulate

from framework.mongo import db
from website import settings

from .utils import mkdirp


user_collection = db['user']

TAB_PATH = os.path.join(settings.ANALYTICS_PATH, 'tables', 'features')
mkdirp(TAB_PATH)


def main():
    users_total = user_collection.find()
    users_jobs = user_collection.find({'jobs': {'$nin': [None, []]}})
    users_schools = user_collection.find({'schools': {'$nin': [None, []]}})
    users_social = user_collection.find({'social': {'$nin': [None, {}]}})
    table = tabulate(
        [
            ['total', 'jobs', 'schools', 'social'],
            [
                users_total.count(),
                users_jobs.count(),
                users_schools.count(),
                users_social.count(),
            ],
        ],
        headers='firstrow',
    )
    with open(os.path.join(TAB_PATH, 'extended-profile.txt'), 'w') as fp:
        fp.write(table)


if __name__ == '__main__':
    main()

