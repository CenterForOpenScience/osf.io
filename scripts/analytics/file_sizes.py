# -*- coding: utf-8 -*-

"""
Summarize distribution of file sizes in OSF git repos.
"""

from __future__ import division

import os

import numpy as np
import tabulate

from website import settings


def walk_collect(path, func):
    sizes = []
    for root, dirs, files in os.walk(path):
        try:
            dirs.remove('.git')
        except ValueError:
            pass
        sizes.extend([
            func(root, file)
            for file in files
        ])
    return sizes


def size_helper(root, file):
    return root, file, os.stat(os.path.join(root, file)).st_size


def size_percentiles():
    sizes = walk_collect(settings.UPLOADS_PATH, size_helper)

    cutoffs = range(2, 102, 2)
    percentiles = np.percentile(
        [size[-1] / 1024 / 1024 for size in sizes],
        cutoffs,
    )

    return tabulate.tabulate(
        zip(cutoffs, percentiles),
        headers=['Percentile', 'Size (MiB)'],
    )


if __name__ == '__main__':
    print(size_percentiles())

