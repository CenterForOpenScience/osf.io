# -*- coding: utf-8 -*-

import os
import matplotlib.pyplot as plt

from framework.mongo import database
from website import settings

from .utils import plot_dates, mkdirp


link_collection = database['privatelink']

FIG_PATH = os.path.join(settings.ANALYTICS_PATH, 'figs', 'features')
mkdirp(FIG_PATH)


def analyze_view_only_links():
    dates = [
        record['date_created']
        for record in link_collection.find({}, {'date_created': True})
    ]
    if not dates:
        return
    fig = plot_dates(dates)
    plt.title('view-only links ({} total)'.format(len(dates)))
    plt.savefig(os.path.join(FIG_PATH, 'view-only-links.png'))
    plt.close()


def analyze_view_only_links_anonymous():
    dates = [
        record['date_created']
        for record in link_collection.find(
            {'anonymous': True},
            {'date_created': True},
        )
    ]
    if not dates:
        return
    fig = plot_dates(dates)
    plt.title('anonymous view-only links ({} total)'.format(len(dates)))
    plt.savefig(os.path.join(FIG_PATH, 'view-only-links-anonymous.png'))
    plt.close()


def main():
    analyze_view_only_links()
    analyze_view_only_links_anonymous()


if __name__ == '__main__':
    main()

