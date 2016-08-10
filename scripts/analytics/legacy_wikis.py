# -*- coding: utf-8 -*-

import os
import sys
from tabulate import tabulate

from framework.mongo import database
from website import settings
from website.addons.wiki import settings as wiki_settings

from .utils import mkdirp

wiki_collection = database['nodewikipage']

TAB_PATH = os.path.join(settings.ANALYTICS_PATH, 'tables', 'features')
mkdirp(TAB_PATH)

def get_wiki_counts():

    wikis_total = wiki_collection.find()

    query_legacy = {'date': {'$lt': WIKI_CHANGE_DATE}}

    wikis_legacy = wiki_collection.find(query_legacy)
    total_size = 0
    largest = 0
    for entry in wikis_legacy:
        size = sys.getsizeof(entry.get('content'))
        total_size += size
        if size > largest:
            largest = size

    try:
        average_size = (total_size / wikis_legacy.count())
    except ZeroDivisionError:
        average_size = 0

    return {
        'total': wikis_total.count(),
        'legacy': wikis_legacy.count(),
        'average_size': average_size,
        'largest': largest,
    }


def main():

    counts = get_wiki_counts()
    keys = ['total', 'legacy', 'average_size', 'largest']

    table = tabulate(
        [[counts[key] for key in keys]],
        headers=keys,
    )

    with open(os.path.join(TAB_PATH, 'legacy_wikis.txt'), 'w') as fp:
        fp.write(table)


if __name__ == '__main__':
    main()

