#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Migration script for Search-enabled Models.'''
from __future__ import absolute_import

import logging
from modularodm.query.querydialect import DefaultQueryDialect as Q
from scripts import utils as script_utils
from website.models import Node
from framework.auth import User
import website.search.search as search

from website.app import init_app

logger = logging.getLogger(__name__)

app = init_app("website.settings", set_backends=True, routes=True)


def migrate_nodes():
    n_iter = 0
    nodes = Node.find(Q('is_public', 'eq', True) & Q('is_deleted', 'eq', False))
    for node in nodes:
        node.update_search()
        n_iter += 1

    logger.info('Nodes migrated: {}'.format(n_iter))


def migrate_users():
    n_migr = 0
    n_iter = 0
    for user in User.find():
        if user.is_active:
            user.update_search()
            n_migr += 1
        n_iter += 1

    logger.info('Users iterated: {0}\nUsers migrated: {1}'.format(n_iter, n_migr))


def main():

    script_utils.add_file_logger(logger, __file__)
    ctx = app.test_request_context()
    ctx.push()

    search.delete_all()
    search.create_index()
    migrate_nodes()
    migrate_users()

    ctx.pop()


if __name__ == '__main__':
    main()
