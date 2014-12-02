# -*- coding: utf-8 -*-
"""Scripts for counting recently added users by email domain; pushes results
to the specified project.
"""

import csv
import datetime
import collections
from cStringIO import StringIO

import requests
from dateutil.relativedelta import relativedelta

from framework.auth import Auth
from framework.mongo import database

from website import models
from website.app import app, init_app
from website.addons.osfstorage import utils as storage_utils


NODE_ID = '95nv8'
USER_ID = 'icpnw'
FILE_NAME = 'daily-users.csv'
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
    init_app()
    node = models.Node.load(NODE_ID)
    user = models.User.load(USER_ID)
    emails = get_emails_since(TIME_DELTA)
    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerow(['affiliation', 'count'])
    writer.writerows(emails)
    nchar = sio.tell()
    sio.seek(0)
    with app.test_request_context():
        upload_url = storage_utils.get_upload_url(
            node,
            user,
            nchar,
            'text/csv',
            FILE_NAME,
        )
    requests.put(
        upload_url,
        data=sio,
        headers={'Content-Type': 'text/csv'},
    )


if __name__ == '__main__':
    main()
