#!/usr/bin/env python
# encoding: utf-8
"""Tabulate files usage per user, both by files uploaded by the user (personal)
and files uploaded to any project on which the user is a contributor (group).
Currently outputs results to .csv files in the current working directory.
"""

import datetime
import collections

from django.utils import timezone

from website import models
from website.app import init_app

from scripts.analytics import utils


def count_usage():
    """Count personal and group file space usage.

    :returns: Tuple of dicts mapping users to dicts mapping version IDs to sizes
    """
    personal = collections.defaultdict(dict)
    group = collections.defaultdict(dict)
    for node in models.Node.find():
        tree = node.get_addon('osfstorage').file_tree
        if not tree:
            continue
        for record in tree.children:
            for version in record.versions:
                size = version.size or version.metadata.get('size')
                if not size:
                    continue
                size = int(size)
                personal[version.creator][version._id] = size
                for user in node.contributors:
                    group[user][version._id] = size
    return personal, group


def write_counts(counts, outname):
    summed_counts = sorted(
        [
            (user, sum(values.values()))
            for user, values in counts.iteritems()
        ],
        key=lambda item: item[1],
        reverse=True,
    )
    with open(outname, 'w') as fp:
        utils.make_csv(
            fp,
            [
                [
                    user._id,
                    user.fullname,
                    total,
                ]
                for user, total in summed_counts
            ],
            [
                'user-id',
                'user-name',
                'usage',
            ],
        )


def main():
    now = timezone.now().strftime('%Y-%m-%d')
    personal, group = count_usage()
    write_counts(personal, 'usage-personal-{0}.csv'.format(now))
    write_counts(group, 'usage-group-{0}.csv'.format(now))


if __name__ == '__main__':
    init_app(set_backends=True, routes=False)
    main()
