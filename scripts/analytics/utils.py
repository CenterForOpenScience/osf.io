# -*- coding: utf-8 -*-

import os
import unicodecsv as csv
from bson import ObjectId

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

import requests

from website import util
from website import settings as website_settings


def oid_to_datetime(oid):
    return ObjectId(oid).generation_time


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError:
        pass


def plot_dates(dates, *args, **kwargs):

    if dates is None or len(dates) == 0:
        return -1

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


def send_file(app, path, content_type, file_like, node, user):
    """Upload file to OSF.
    :param str app: Flask app
    :param str path: The path of the requested file or folder
    :param str content_type: Value for header 'Content-Type'
    :param StringIO file_like: file-like stream to upload
    :param Node node: The node being accessed
    :param User user: The user whose cookie will be used
    """

    if not node:
        return
    node_id = node._id

    if not user:
        return
    cookies = {website_settings.COOKIE_NAME:user.get_or_create_cookie()}

    file_like.seek(0)
    upload_url = util.waterbutler_api_url_for(node_id, 'osfstorage', path)

    # with app.test_request_context():
    #     upload_url = util.waterbutler_url_for('upload', 'osfstorage', name, node, user=user)

    requests.put(
        upload_url,
        data=file_like,
        headers={'Content-Type': content_type},
        cookies=cookies,
    )
