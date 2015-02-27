#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Migration script for Search-enabled Models.'''
from __future__ import absolute_import

from elasticsearch import helpers
from modularodm.query.querydialect import DefaultQueryDialect as Q

from framework.auth import User
from website.models import Node
from website.app import init_app
import website.search.search as search
from website.search.elastic_search import es


app = init_app("website.settings", set_backends=True, routes=True)


def migrate_nodes(index):
    for node in Node.find(Q('is_public', 'eq', True)
            & Q('is_deleted', 'eq', False)):
        search.update_node(node, index=index)


def migrate_users(index):
    for user in User.find(Q('is_registered', 'eq', True)
            & Q('date_confirmed', 'ne', None)):
        search.update_user(user, index=index)


def main():

    ctx = app.test_request_context()
    ctx.push()
    index = set_up_index()
    migrate_nodes(index)
    migrate_users(index)
    set_up_alias(index)

    ctx.pop()


def set_up_index():
    alias = es.indices.get_aliases(index='website')

    if not alias or not alias.keys() or 'website' in alias.keys():
        # Deal with empty indices or the first migration
        index = 'website_v1'
        search.create_index(index=index)
        helpers.reindex(es, 'website', index)
        es.indices.delete(index='website')
        es.indices.put_alias('website', index)
    else:
        # Increment version
        version = int(alias.keys()[0][-1]) + 1
        index = 'website_v{}'.format(version)
        search.create_index(index=index)
    return index


def set_up_alias(index):
    alias = es.indices.get_aliases(index='website')
    if alias:
        es.indices.delete_alias(index='website', name='_all', ignore=404)
    es.indices.put_alias('website', index)


if __name__ == '__main__':
    main()
