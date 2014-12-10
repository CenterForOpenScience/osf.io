# -*- coding: utf-8 -*-

import os
import csv
import datetime
from bson import ObjectId
from cStringIO import StringIO

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

import requests

from website.addons.osfstorage import utils as storage_utils


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


def make_csv(rows, headers=None):
    sio = StringIO()
    writer = csv.writer(sio)
    if headers:
        writer.writerow(headers)
    writer.writerows(rows)
    nchar = sio.tell()
    sio.seek(0)
    return sio, nchar


def send_file(app, name, content_type, file_like, nchar, node, user):
    """Upload file to OSF."""
    with app.test_request_context():
        upload_url = storage_utils.get_upload_url(
            node,
            user,
            nchar,
            content_type,
            name,
        )
    requests.put(
        upload_url,
        data=file_like,
        headers={'Content-Type': content_type},
    )
