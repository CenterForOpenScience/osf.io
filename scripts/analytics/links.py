# -*- coding: utf-8 -*-

import os
import matplotlib.pyplot as plt

from framework.mongo import db
from website import settings

from utils import plot_dates


link_collection = db['privatelink']

ROOT_PATH = settings.parent_dir(settings.BASE_PATH)
FIG_PATH = os.path.join(ROOT_PATH, 'figs', 'features')


def analyze_view_only_link_dates():
    dates = [
        record['date_created']
        for record in link_collection.find({}, {'date_created': True})
    ]
    fig = plot_dates(dates)
    plt.title('view-only links ({0} total)'.format(len(dates)))
    plt.savefig(os.path.join(FIG_PATH, 'view-only-link-actions.png'))
    plt.close()


if __name__ == '__main__':
    analyze_view_only_link_dates()

