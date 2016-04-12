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


def send_file(name, content_type, stream, node, user, create=True, path='/'):
    """Upload file to OSF using waterbutler v1 api
    :param str name: The name of the requested file
    :param str content_type: Content-Type
    :param StringIO stream: file-like stream to be uploaded
    :param Node node: Project Node
    :param User user: User whose cookie will be used
    :param Bool create: Create or update file
    :param str path: Waterbutler V1 path of the requested file
    """

    if not node:
        return
    node_id = node._id

    if not user:
        return
    cookies = {website_settings.COOKIE_NAME:user.get_or_create_cookie()}

    # create a new folder
    if stream is None:
        upload_url = util.waterbutler_api_url_for(node_id, 'osfstorage', path, kind='folder', name=name)
        print('create folder: url={}'.format(upload_url))
        resp = requests.put(
            upload_url,
            headers={'Content-Type': content_type},
            cookies=cookies,
        )
        if resp.status_code != 201:
            resp.raise_for_status()
        return resp

    # create or update a file
    stream.seek(0)
    if create:
        upload_url = util.waterbutler_api_url_for(node_id, 'osfstorage', path, kind='file', name=name)
        print('create file: url={}'.format(upload_url))
    else:
        path = '/{}'.format(name)
        upload_url = util.waterbutler_api_url_for(node_id, 'osfstorage', path, kind='file')
        print('update file: url={}'.format(upload_url))
    resp = requests.put(
        upload_url,
        data=stream,
        headers={'Content-Type': content_type},
        cookies=cookies,
    )

    if resp.status_code not in [200, 201, 503, 409]:
        resp.raise_for_status()
    if resp.status_code == 503:
        pass  # forward 503 error back to the caller
    elif resp.status_code == 409:
        print('I/O Warning: cannot create new file/folder that already exists.') # this should never appear
    return resp
