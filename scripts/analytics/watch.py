# -*- coding: utf-8 -*-

import os
import matplotlib.pyplot as plt

from framework.mongo import database
from website import settings

from .utils import plot_dates, oid_to_datetime, mkdirp


watch_collection = database['watchconfig']

FIG_PATH = os.path.join(settings.ANALYTICS_PATH, 'figs', 'features')
mkdirp(FIG_PATH)


def main():
    watch_configs = watch_collection.find()
    dates_watched = [
        oid_to_datetime(watch_config['_id'])
        for watch_config in watch_configs
    ]
    if not dates_watched:
        return
    fig = plot_dates(dates_watched)
    plt.title('nodes watched ({}) total)'.format(len(dates_watched)))
    plt.savefig(os.path.join(FIG_PATH, 'nodes-watched.png'))
    plt.close()


if __name__ == '__main__':
    main()

