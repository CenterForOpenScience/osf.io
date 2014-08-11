# -*- coding: utf-8 -*-

import os
import re
from bson import ObjectId
import matplotlib.pyplot as plt

from framework.mongo import db
from website import settings
from website.app import init_app

from .utils import plot_dates


log_collection = db['nodelog']
init_app()

ROOT_PATH = settings.parent_dir(settings.BASE_PATH)
FIG_PATH = os.path.join(ROOT_PATH, 'figs', 'addons')
ADDONS = [
    'github',
    's3',
    'figshare',
    'dropbox',
    'dataverse',
]


def oid_to_datetime(oid):
    return ObjectId(oid).generation_time


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
        fig = plot_dates(result['dates'])
        plt.title('{0} configurations: {1} ({2} total)'.format(name, model, len(result['dates'])))
        plt.savefig(os.path.join(FIG_PATH, '{0}-installs-{1}.png'.format(name, model)))
        plt.close()

    log_dates = analyze_addon_logs(name)
    fig = plot_dates(log_dates)
    plt.title('{0} actions ({1} total)'.format(name, len(log_dates)))
    plt.savefig(os.path.join(FIG_PATH, '{0}-actions.png'.format(name)))
    plt.close()


if __name__ == '__main__':
    for addon in ADDONS:
        if addon in settings.ADDONS_AVAILABLE_DICT:
            analyze_addon(addon)

