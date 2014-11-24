#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Migration script for Search-enabled Models.'''
from __future__ import absolute_import
from modularodm.query.querydialect import DefaultQueryDialect as Q
from website.models import Node
from framework.auth import User
import website.search.search as search

from website.app import init_app

app = init_app("website.settings", set_backends=True, routes=True)


def migrate_nodes():
    for node in Node.find(Q('is_public', 'eq', True)
            & Q('is_deleted', 'eq', False)):
        node.update_search()


def migrate_users():
    for user in User.find(Q('is_registered', 'eq', True)
            & Q('date_confirmed', 'ne', None)):
        user.update_search()


def main():

    ctx = app.test_request_context()
    ctx.push()

    search.delete_all()
    search.create_index()
    migrate_nodes()
    migrate_users()

    ctx.pop()


if __name__ == '__main__':
    main()
