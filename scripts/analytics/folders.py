# -*- coding: utf-8 -*-

import os
import matplotlib.pyplot as plt

from framework.mongo import database
from website import settings

from utils import plot_dates, mkdirp


node_collection = database['node']

FIG_PATH = os.path.join(settings.ANALYTICS_PATH, 'figs', 'features')
mkdirp(FIG_PATH)


def main():
    dates = [
        record['date_created']
        for record in node_collection.find(
            {
                'is_collection': True,
                'is_bookmark_collection': {'$ne': True},
            },
            {'date_created': True},
        )
    ]
    if not dates:
        return
    plot_dates(dates)
    plt.title('folders ({0} total)'.format(len(dates)))
    plt.savefig(os.path.join(FIG_PATH, 'folder-actions.png'))
    plt.close()


if __name__ == '__main__':
    main()
