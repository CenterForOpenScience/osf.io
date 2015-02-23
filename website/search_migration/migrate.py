#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Migration script for Search-enabled Models.'''
from __future__ import absolute_import

import logging
from modularodm.query.querydialect import DefaultQueryDialect as Q
from website.models import Node
from framework.auth import User
import website.search.search as search

from website.app import init_app

logger = logging.getLogger(__name__)

app = init_app("website.settings", set_backends=True, routes=True)


def migrate_nodes():
    count = 0
    nodes = Node.find(Q('is_public', 'eq', True) & Q('is_deleted', 'eq', False))
    for node in nodes:
        node.update_search()
        count += 1
    return count


def migrate_users():
    count = 0
    for user in User.find():
        if user.is_active:
            user.update_search()
            count += 1
    return count


def main():

    ctx = app.test_request_context()
    ctx.push()

    search.delete_all()
    search.create_index()
    logger.info("Nodes migrated: {}".format(migrate_nodes()))
    logger.info("Users migrated: {}".format(migrate_users()))

    ctx.pop()


if __name__ == '__main__':
    main()
