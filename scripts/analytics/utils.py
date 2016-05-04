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


def create_object(name, content_type, node, user, stream=None, kind=None, path='/'):
    """Create an object (file/folder) OSF using WaterButler v1 API
    :param str name: The name of the requested file
    :param str content_type: Content-Type
    :param StringIO stream: file-like stream to be uploaded
    :param Node node: Project Node
    :param User user: User whose cookie will be used
    :param str path: Waterbutler V1 path of the requested file
    """

    node_id = node._id
    cookies = {website_settings.COOKIE_NAME: user.get_or_create_cookie()}

    # create or update a file
    url = util.waterbutler_api_url_for(node_id, 'osfstorage', path)
    print('get path: url={}'.format(url))
    resp = requests.get(url, cookies=cookies)
    data = resp.json()['data']

    existing_path = None
    for item in data:
        if item['attributes']['name'] == name:
            existing_path = item['attributes']['path']

    if stream:
        stream.seek(0)

    # create a new file/folder?
    if not existing_path:
        url = util.waterbutler_api_url_for(node_id, 'osfstorage', path, kind=kind, name=name)
        print('create file or folder: url={}'.format(url))
        requests.put(
            url,
            data=stream,
            headers={'Content-Type': content_type},
            cookies=cookies,
        )
    elif kind == 'file':
        # path = '/{}'.format(name)
        url = util.waterbutler_api_url_for(node_id, 'osfstorage', existing_path, kind=kind)
        print('update file: url={}'.format(url))
        requests.put(
            url,
            data=stream,
            headers={'Content-Type': content_type},
            cookies=cookies,
        )
