# -*- coding: utf-8 -*-

import os
import matplotlib.pyplot as plt

from framework.mongo import database
from website import settings

from .utils import plot_dates, mkdirp


log_collection = database['nodelog']

FIG_PATH = os.path.join(settings.ANALYTICS_PATH, 'figs', 'logs')
mkdirp(FIG_PATH)


def analyze_log_action(action):
    logs = log_collection.find({'action': action})
    dates = [
        log['date']
        for log in logs
        if log['date']
    ]
    if not dates:
        return
    fig = plot_dates(dates)
    plt.title('logged actions for {} ({} total)'.format(action, len(dates)))
    plt.savefig(os.path.join(FIG_PATH, '{}.png'.format(action)))
    plt.close()


def main():
    actions = log_collection.find(
        {},
        {'action': True}
    ).distinct(
        'action'
    )
    for action in actions:
        analyze_log_action(action)


if __name__ == '__main__':
    main()

