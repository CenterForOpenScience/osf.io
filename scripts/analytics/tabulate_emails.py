# -*- coding: utf-8 -*-
"""Scripts for counting recently added users by email domain; pushes results
to the specified project.
"""

import datetime
import collections

from dateutil.relativedelta import relativedelta

from framework.auth import Auth
from framework.mongo import database

from website import models
from website.app import app, init_app

from scripts.analytics import utils


NODE_ID = '95nv8'
USER_ID = 'icpnw'
FILE_NAME = 'daily-users.csv'
CONTENT_TYPE = 'text/csv'
TIME_DELTA = relativedelta(days=1)


def get_emails(query=None):
    users = database['user'].find(query, {'username': True})
    counts = collections.Counter(
        user['username'].split('@')[-1]
        for user in users
    )
    return counts.most_common()


def get_emails_since(delta):
    return get_emails({
        'date_confirmed': {
            '$gte': datetime.datetime.utcnow() - delta,
        }
    })


def main():
    node = models.Node.load(NODE_ID)
    user = models.User.load(USER_ID)
    emails = get_emails_since(TIME_DELTA)
    sio, nchar = utils.make_csv(emails, ['affiliation', 'count'])
    utils.send_file(app, FILE_NAME, CONTENT_TYPE, sio, nchar, node, user)


if __name__ == '__main__':
    init_app()
    main()
