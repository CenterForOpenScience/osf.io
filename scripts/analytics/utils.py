# -*- coding: utf-8 -*-

import os
import unicodecsv as csv
from bson import ObjectId

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import requests

from website import util


def oid_to_datetime(oid):
    return ObjectId(oid).generation_time


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def plot_dates(dates, *args, **kwargs):
    """Plot date histogram."""
    fig = plt.figure()
    ax = fig.add_subplot(111)

    ax.hist(
        [mdates.date2num(each) for each in dates],
        *args, **kwargs
    )

    fig.autofmt_xdate()
    ax.format_xdata = mdates.DateFormatter('%Y-%m-%d')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

    return fig


def make_csv(fp, rows, headers=None):
    writer = csv.writer(fp)
    if headers:
        writer.writerow(headers)
    writer.writerows(rows)


def send_file(app, name, content_type, file_like, node, user):
    """Upload file to OSF."""
    file_like.seek(0)
    with app.test_request_context():
        upload_url = util.waterbutler_url_for('upload', 'osfstorage', name, node, user=user)
    requests.put(
        upload_url,
        data=file_like,
        headers={'Content-Type': content_type},
    )
