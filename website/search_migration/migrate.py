#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Migration script for Search-enabled Models.'''
from __future__ import absolute_import

import logging

from elasticsearch import helpers
from modularodm.query.querydialect import DefaultQueryDialect as Q

from framework.auth import User
from website.models import Node
from website.app import init_app
import website.search.search as search
from website.search.elastic_search import es


app = init_app("website.settings", set_backends=True, routes=True)
logger = logging.getLogger(__name__)

def migrate_nodes(index):
    logger.info("Migrating nodes")
    for node in Node.find(Q('is_public', 'eq', True)
            & Q('is_deleted', 'eq', False)):
        search.update_node(node, index=index)


def migrate_users(index):
    logger.info("Migrating users")
    for user in User.find(Q('is_registered', 'eq', True)
            & Q('date_confirmed', 'ne', None)):
        search.update_user(user, index=index)


def migrate(delete):

    ctx = app.test_request_context()
    ctx.push()
    index = set_up_index()

    migrate_nodes(index)
    migrate_users(index)

    set_up_alias(index)

    if delete:
        delete_old(index)

    ctx.pop()


def set_up_index():
    alias = es.indices.get_aliases(index='website')

    if not alias or not alias.keys() or 'website' in alias.keys():
        # Deal with empty indices or the first migration
        index = 'website_v1'
        search.create_index(index=index)
        logger.info("Reindexing website to website_v1")
        helpers.reindex(es, 'website', index)
        logger.info("Deleting website index")
        es.indices.delete(index='website')
        es.indices.put_alias('website', index)
    else:
        # Increment version
        version = int(alias.keys()[0][-1]) + 1
        logger.info("Incrementing index version to {}".format(version))
        index = 'website_v{}'.format(version)
        search.create_index(index=index)
        logger.info("{} index created".format(index))
    return index


def set_up_alias(index):
    alias = es.indices.get_aliases(index='website')
    if alias:
        logger.info("Removing old aliases...")
        es.indices.delete_alias(index='website', name='_all', ignore=404)
    es.indices.put_alias('website', index)


def delete_old(index):
    old_version = int(index[-1]) - 1
    if old_version < 1:
        logger.info("No index before {} to delete".format(index))
        pass
    else:
        old_index = index[:-1] + str(old_version)
        logger.info("Deleting {}".format(old_index))
        es.indices.delete(index=old_index, ignore=404)


if __name__ == '__main__':
    migrate(False)
