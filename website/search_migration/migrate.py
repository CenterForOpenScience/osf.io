#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Migration script for Search-enabled Models.'''
from __future__ import absolute_import

import logging

from django.db.models import Q
from django.utils import timezone
from elasticsearch import helpers

import website.search.search as search
from framework.database import paginated
from scripts import utils as script_utils
from osf.models import OSFUser, Institution, AbstractNode
from website import settings
from website.app import init_app
from website.search.elastic_search import client as es_client
from website.search.search import update_institution

logger = logging.getLogger(__name__)

def migrate_nodes(index, query=None):
    logger.info('Migrating nodes to index: {}'.format(index))
    node_query = Q(is_public=True, is_deleted=False)
    if query:
        node_query = query & node_query
    total = AbstractNode.objects.filter(node_query).count()
    increment = 100
    total_pages = (total // increment) + 1
    pages = paginated(AbstractNode, query=node_query, increment=increment, each=False, include=['contributor__user__guids'])

    for page_number, page in enumerate(pages):
        logger.info('Updating page {} / {}'.format(page_number + 1, total_pages))
        AbstractNode.bulk_update_search(page, index=index)

    logger.info('Nodes migrated: {}'.format(total))


def migrate_users(index):
    logger.info('Migrating users to index: {}'.format(index))
    n_migr = 0
    n_iter = 0
    users = paginated(OSFUser, query=None, each=True)
    for user in users:
        if user.is_active:
            search.update_user(user, index=index)
            n_migr += 1
        n_iter += 1

    logger.info('Users iterated: {0}\nUsers migrated: {1}'.format(n_iter, n_migr))

def migrate_institutions(index):
    for inst in Institution.objects.filter(is_deleted=False):
        update_institution(inst, index)

def migrate(delete, index=None, app=None):
    index = index or settings.ELASTIC_INDEX
    app = app or init_app('website.settings', set_backends=True, routes=True)

    script_utils.add_file_logger(logger, __file__)
    # NOTE: We do NOT use the app.text_request_context() as a
    # context manager because we don't want the teardown_request
    # functions to be triggered
    ctx = app.test_request_context()
    ctx.push()

    new_index = set_up_index(index)
    start_time = timezone.now()

    if settings.ENABLE_INSTITUTIONS:
        migrate_institutions(new_index)
    migrate_nodes(new_index)
    migrate_users(new_index)

    set_up_alias(index, new_index)

    # migrate nodes modified since start
    migrate_nodes(new_index, query=Q(date_modified__gte=start_time))

    if delete:
        delete_old(new_index)

    ctx.pop()

def set_up_index(idx):
    alias = es_client().indices.get_aliases(index=idx)

    if not alias or not alias.keys() or idx in alias.keys():
        # Deal with empty indices or the first migration
        index = '{}_v1'.format(idx)
        search.create_index(index=index)
        logger.info('Reindexing {0} to {1}_v1'.format(idx, idx))
        helpers.reindex(es_client(), idx, index)
        logger.info('Deleting {} index'.format(idx))
        es_client().indices.delete(index=idx)
        es_client().indices.put_alias(idx, index)
    else:
        # Increment version
        version = int(alias.keys()[0].split('_v')[1]) + 1
        logger.info('Incrementing index version to {}'.format(version))
        index = '{0}_v{1}'.format(idx, version)
        search.create_index(index=index)
        logger.info('{} index created'.format(index))
    return index


def set_up_alias(old_index, index):
    alias = es_client().indices.get_aliases(index=old_index)
    if alias:
        logger.info('Removing old aliases to {}'.format(old_index))
        es_client().indices.delete_alias(index=old_index, name='_all', ignore=404)
    logger.info('Creating new alias from {0} to {1}'.format(old_index, index))
    es_client().indices.put_alias(old_index, index)


def delete_old(index):
    old_version = int(index.split('_v')[1]) - 1
    if old_version < 1:
        logger.info('No index before {} to delete'.format(index))
        pass
    else:
        old_index = index.split('_v')[0] + '_v' + str(old_version)
        logger.info('Deleting {}'.format(old_index))
        es_client().indices.delete(index=old_index, ignore=404)


if __name__ == '__main__':
    migrate(False)
