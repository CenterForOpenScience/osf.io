# -*- coding: utf-8 -*-

import os
import matplotlib.pyplot as plt

from framework.mongo import database
from website import settings

from utils import plot_dates, mkdirp


comment_collection = database['comment']

FIG_PATH = os.path.join(settings.ANALYTICS_PATH, 'figs', 'features')
mkdirp(FIG_PATH)


def main():
    dates = [
        record['date_created']
        for record in comment_collection.find({}, {'date_created': True})
    ]
    fig = plot_dates(dates)
    plt.title('comments ({0} total)'.format(len(dates)))
    plt.savefig(os.path.join(FIG_PATH, 'comment-actions.png'))
    plt.close()


if __name__ == '__main__':
    main()

