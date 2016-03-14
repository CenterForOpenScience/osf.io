# -*- coding: utf-8 -*-
"""Scripts for counting recently added users by email domain; pushes results
to the specified project.
"""

import datetime
import collections
from cStringIO import StringIO

from framework.mongo import database

from website import models
from website.app import app, init_app

from scripts.analytics import utils
from scripts.analytics import settings


def get_emails(query=None):
    users = database['user'].find(query, {'username': True})
    counts = collections.Counter(
        user['username'].split('@')[-1]
        for user in users
    )
    return counts.most_common()


def get_emails_since(delta):
    return get_emails({
        'is_registered': True,
        'password': {'$ne': None},
        'is_merged': {'$ne': True},
        'date_confirmed': {'$gte': datetime.datetime.utcnow() - delta},
    })


def main():
    node = models.Node.load(settings.TABULATE_EMAILS_NODE_ID)
    user = models.User.load(settings.TABULATE_EMAILS_USER_ID)
    emails = get_emails_since(settings.TABULATE_EMAILS_TIME_DELTA)
    sio = StringIO()
    utils.make_csv(sio, emails, ['affiliation', 'count'])
    utils.send_file(settings.TABULATE_EMAILS_FILE_NAME, settings.TABULATE_EMAILS_CONTENT_TYPE, sio, node, user)


if __name__ == '__main__':
    init_app()
    main()
