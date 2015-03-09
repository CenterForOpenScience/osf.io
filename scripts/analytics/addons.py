# -*- coding: utf-8 -*-

import os
import re
import matplotlib.pyplot as plt

from framework.mongo import database
from website import settings
from website.app import init_app

from .utils import plot_dates, oid_to_datetime, mkdirp


log_collection = database['nodelog']

FIG_PATH = os.path.join(settings.ANALYTICS_PATH, 'figs', 'addons')
mkdirp(FIG_PATH)

ADDONS = [
    'github',
    's3',
    'figshare',
    'dropbox',
    'dataverse',
]


def get_collection_datetimes(collection, _id='_id', query=None):
    query = query or {}
    return [
        oid_to_datetime(record[_id])
        for record in collection.find({}, {_id: True})
    ]


def analyze_model(model):

    dates = get_collection_datetimes(model._storage[0].store)
    return {
        'dates': dates,
        'count': len(dates),
    }


def analyze_addon_installs(name):

    config = settings.ADDONS_AVAILABLE_DICT[name]

    results = {
        key: analyze_model(model)
        for key, model in config.settings_models.iteritems()
    }

    return results


def analyze_addon_logs(name):

    pattern = re.compile('^{0}'.format(name), re.I)
    logs = log_collection.find({'action': {'$regex': pattern}}, {'date': True})
    return [
        record['date']
        for record in logs
    ]


def analyze_addon(name):

    installs = analyze_addon_installs(name)
    for model, result in installs.iteritems():
        if not result['dates']:
            continue
        fig = plot_dates(result['dates'])
        plt.title('{} configurations: {} ({} total)'.format(name, model, len(result['dates'])))
        plt.savefig(os.path.join(FIG_PATH, '{}-installs-{}.png'.format(name, model)))
        plt.close()

    log_dates = analyze_addon_logs(name)
    if not log_dates:
        return
    fig = plot_dates(log_dates)
    plt.title('{} actions ({} total)'.format(name, len(log_dates)))
    plt.savefig(os.path.join(FIG_PATH, '{}-actions.png'.format(name)))
    plt.close()


def main():
    init_app(routes=False)
    for addon in ADDONS:
        if addon in settings.ADDONS_AVAILABLE_DICT:
            analyze_addon(addon)


if __name__ == '__main__':
    main()
