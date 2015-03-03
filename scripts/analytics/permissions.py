# -*- coding: utf-8 -*-

import os
from collections import Counter
from tabulate import tabulate

from framework.mongo import database
from website import settings

from .utils import mkdirp


node_collection = database['node']

TAB_PATH = os.path.join(settings.ANALYTICS_PATH, 'tables', 'features')
mkdirp(TAB_PATH)


def main():
    counter = Counter()
    for node in node_collection.find():
        permissions = node.get('permissions')
        # TODO: Shouldn't need this check
        if not permissions:
            continue
        counter.update([
            tuple(permissions)
            for _, permissions in permissions.items()
        ])
    table = tabulate(
        [
            ['total', 'admin', 'write', 'read'],
            [
                sum(counter.values()),
                counter[('read', 'write', 'admin', )],
                counter[('read', 'write', )],
                counter[('read', )]
            ]
        ],
        headers='firstrow',
    )
    with open(os.path.join(TAB_PATH, 'permissions.txt'), 'w') as fp:
        fp.write(table)


if __name__ == '__main__':
    main()

