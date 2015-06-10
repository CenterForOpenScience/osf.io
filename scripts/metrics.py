#!/usr/bin/env python
# encoding: utf-8
"""Legacy metrics script."""

import os

import tabulate
from modularodm import Q

from framework.analytics import get_basic_counters

from website import models
from website import settings
from website.app import init_app
from website.addons.osfstorage.model import OsfStorageFileNode
from website.addons.osfstorage.model import OsfStorageTrashedFileNode


def main():
    number_users = models.User.find().count()

    projects = models.Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True)
    )
    projects_forked = list(models.Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True) &
        Q('is_fork', 'eq', True)
    ))
    projects_registered = models.Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True) &
        Q('is_registration', 'eq', True)
    )

    pf = []
    for p in projects_forked:
        if not p.contributors[0]:
            continue
        name = p.contributors[0].fullname
        if unicode(name) not in [u'Jeffres R. Spies', 'Brian A. Nosek']:
            pf.append(p)

    pr = []
    for p in projects_registered:
        name = p.contributors[0].fullname
        if not p.contributors[0]:
            continue
        if not unicode(name)==u'Jeffrey R. Spies' and not unicode(name)==u'Brian A. Nosek':
            pr.append(p)

    number_projects = len(projects)
    number_projects_public = models.Node.find(
        Q('category', 'eq', 'project') &
        Q('is_deleted', 'eq', False) &
        Q('is_folder', 'ne', True) &
        Q('is_public', 'eq', True)
    ).count()
    number_projects_forked = len(pf)

    number_projects_registered = len(pr)

    ##############

    number_downloads_total = 0
    number_downloads_unique = 0

    contributors_per_project = []

    contrib = {}

    for project in projects:
        contributors_per_project.append(len(project.contributors))
        for person in project.contributors:
            if not person:
                continue
            if person._id not in contrib:
                contrib[person._id] = []
            for neighbor in project.contributors:
                if not neighbor:
                    continue
                if neighbor._id not in contrib[person._id]:
                    contrib[person._id].append(neighbor._id)

        addon = project.get_addon('osfstorage')

        for filenode in OsfStorageFileNode.find(Q('node_settings', 'eq', addon) & Q('kind', 'eq', 'file')):
            for idx, version in enumerate(filenode.versions):
                page = ':'.join(['download', project._id, filenode._id, str(idx)])
                unique, total = get_basic_counters(page)
                number_downloads_total += total or 0
                number_downloads_unique += unique or 0

        for filenode in OsfStorageTrashedFileNode.find(Q('node_settings', 'eq', addon) & Q('kind', 'eq', 'file')):
            for idx, version in enumerate(filenode.versions):
                page = ':'.join(['download', project._id, filenode._id, str(idx)])
                unique, total = get_basic_counters(page)
                number_downloads_total += total or 0
                number_downloads_unique += unique or 0

    table = tabulate.tabulate(
        [
            ['number_users', number_users],
            ['number_projects', number_projects],
            ['number_projects_public', number_projects_public],
            ['number_projects_forked', number_projects_forked],
            ['number_projects_registered', number_projects_registered],
            ['number_downloads_total', number_downloads_total],
            ['number_downloads_unique', number_downloads_unique],
        ],
        headers=['label', 'value'],
    )

    with open(os.path.join(settings.ANALYTICS_PATH, 'legacy.txt'), 'w') as fp:
        fp.write(table)


if __name__ == '__main__':
    init_app()
    main()
