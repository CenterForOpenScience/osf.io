#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Migration script for Search-enabled Models."""
from __future__ import absolute_import
from math import ceil
import functools
import logging

from django.db import connection
from django.core.paginator import Paginator
from elasticsearch2 import helpers

import website.search.search as search
from website.search.elastic_search import client
from website.search_migration import (
    enable_private_search,
    JSON_UPDATE_NODES_SQL, JSON_DELETE_NODES_SQL,
    JSON_UPDATE_FILES_SQL, JSON_DELETE_FILES_SQL,
    JSON_UPDATE_USERS_SQL, JSON_DELETE_USERS_SQL)
from scripts import utils as script_utils
from osf.models import OSFUser, Institution, AbstractNode, BaseFileNode, Preprint, OSFGroup, CollectionSubmission, Comment
from website import settings
from website.app import init_app
from website.search.elastic_search import client as es_client
from website.search.elastic_search import bulk_update_cgm
from website.search.elastic_search import PROJECT_LIKE_TYPES
from website.search.elastic_search import es_index
from website.search.elastic_search import comments_to_doc
from website.search.elastic_search import node_includes_wiki
from website.search.search import update_institution, bulk_update_collected_metadata
from website.search.util import unicode_normalize
from addons.wiki.models import WikiPage
from addons.osfstorage.models import OsfStorageFile

logger = logging.getLogger(__name__)

# see:
# - website.search.elastic_search.update_user
# - website.search.elastic_search.update_file
# - website.search.elastic_search.serialize_node
# - website.search.elastic_search.create_index
def fill_and_normalize(docs):
    assert docs

    doc_op_type = docs[0]['_op_type']
    if doc_op_type != 'update':
        return

    doc_type = docs[0]['_type']
    if doc_type == 'user':
        for doc in docs:
            d = doc['doc']
            d['sort_user_name'] = d['user']
            normalized_names = {}
            for key, val in d['names'].items():
                if val is not None:
                    normalized_names[key] = unicode_normalize(val)
            d['normalized_user'] = normalized_names['fullname']
            d['normalized_names'] = normalized_names

            ongoing_list = ('job', 'job_department', 'job_title',
                            'school', 'school_department', 'school_degree')
            for suffix in ongoing_list:
                name = 'ongoing_' + suffix
                d[name] = unicode_normalize(d[name])
    elif doc_type == 'file':
        for doc in docs:
            d = doc['doc']
            name = d['name']
            d['sort_file_name'] = name
            d['sort_node_name'] = d['node_title']
            d['normalized_name'] = unicode_normalize(name)
            normalized_tags = []
            for tag in d['tags']:
                normalized_tags.append(unicode_normalize(tag))
            d['normalized_tags'] = normalized_tags

            creator_name = d['creator_name']
            d['creator_name'] = unicode_normalize(creator_name)
            modifier_name = d['modifier_name']
            d['modifier_name'] = unicode_normalize(modifier_name)
            f = OsfStorageFile.load(d['id'])
            comments = {}
            if f:
                file_guid = f.get_guid(create=False)
                if file_guid:
                    comments = comments_to_doc(file_guid._id)
            d['comments'] = comments
    elif doc_type in PROJECT_LIKE_TYPES:
        for doc in docs:
            d = doc['doc']
            title = d['title']
            d['sort_node_name'] = title
            d['normalized_title'] = unicode_normalize(title)
            description = d['description']
            if description:
                d['normalized_description'] = unicode_normalize(description)
            normalized_tags = []
            for tag in d['tags']:
                normalized_tags.append(unicode_normalize(tag))
            d['normalized_tags'] = normalized_tags

            creator_name = d['creator_name']
            d['creator_name'] = unicode_normalize(creator_name)
            modifier_name = d['modifier_name']
            d['modifier_name'] = unicode_normalize(modifier_name)
            if node_includes_wiki():
                wikis = d['wikis']
                if isinstance(wikis, list):
                    new_wikis = {}
                    for kv in wikis:
                        if isinstance(kv, dict):
                            for k, v in kv.items():
                                new_wikis[k] = v
                    wikis = new_wikis
                elif not isinstance(wikis, dict):
                    wikis = {}
                normalized_wikis = {}
                normalized_wiki_names = []
                for wikiname, wikidata in wikis.items():
                    wikiname = unicode_normalize(wikiname)
                    normalized_wikis[wikiname] = unicode_normalize(wikidata)
                    normalized_wiki_names.append(wikiname)
                d['wikis'] = normalized_wikis
                d['wiki_names'] = normalized_wiki_names
            else:  # clear
                d['wikis'] = None
                d['wiki_names'] = None
            node = AbstractNode.load(doc['_id'])
            d['comments'] = comments_to_doc(node._id)

def sql_migrate(index, sql, max_id, increment, es_args=None, **kwargs):
    """ Run provided SQL and send output to elastic.

    :param str index: Elastic index to update (formatted into `sql`)
    :param str sql: SQL to format and run. See __init__.py in this module
    :param int max_id: Last known object id. Indicates when to stop paging
    :param int increment: Page size
    :param  dict es_args:  Dict or None, to pass to `helpers.bulk`
    :kwargs: Additional format arguments for `sql` arg

    :return int: Number of migrated objects
    """
    if es_args is None:
        es_args = {}
    total_pages = int(ceil(max_id / float(increment)))
    total_objs = 0
    page_start = 0
    page_end = 0
    page = 0
    while page_end <= (max_id + increment):
        page += 1
        page_end += increment
        if page <= total_pages:
            logger.info('Updating page {} / {}'.format(page_end / increment, total_pages))
        else:
            # An extra page is included to cover the edge case where:
            #       max_id == (total_pages * increment) - 1
            # and two additional objects are created during runtime.
            logger.info('Cleaning up...')
        with connection.cursor() as cursor:
            cursor.execute(sql.format(
                index=index,
                page_start=page_start,
                page_end=page_end,
                enable_private_search=enable_private_search(settings.ENABLE_PRIVATE_SEARCH),
                **kwargs))
            ser_objs = cursor.fetchone()[0]
            if ser_objs:
                total_objs += len(ser_objs)
                fill_and_normalize(ser_objs)
                helpers.bulk(client(), ser_objs, **es_args)
        page_start = page_end
    return total_objs

def migrate_nodes(index, delete, increment=10000):
    logger.info('Migrating nodes to index: {}'.format(index))
    last = AbstractNode.objects.last()
    if last is None:
        logger.info('0 node migrated')
        return
    max_nid = last.id
    total_nodes = sql_migrate(
        index,
        JSON_UPDATE_NODES_SQL,
        max_nid,
        increment,
        spam_flagged_removed_from_search=settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH)
    logger.info('{} nodes migrated'.format(total_nodes))
    if delete:
        logger.info('Preparing to delete old node documents')
        max_nid = AbstractNode.objects.last().id
        total_nodes = sql_migrate(
            index,
            JSON_DELETE_NODES_SQL,
            max_nid,
            increment,
            es_args={'raise_on_error': False},  # ignore 404s
            spam_flagged_removed_from_search=settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH)
        logger.info('{} nodes marked deleted'.format(total_nodes))

def migrate_preprints(index, delete):
    logger.info('Migrating preprints to index: {}'.format(index))
    preprints = Preprint.objects.order_by('-id')
    increment = 100
    paginator = Paginator(preprints, increment)
    for page_number in paginator.page_range:
        logger.info('Updating page {} / {}'.format(page_number, paginator.num_pages))
        Preprint.bulk_update_search(paginator.page(page_number).object_list, index=index)

def migrate_preprint_files(index, delete):
    logger.info('Migrating preprint files to index: {}'.format(index))
    valid_preprints = Preprint.objects.all()
    valid_preprint_files = BaseFileNode.objects.filter(preprint__in=valid_preprints).order_by('-id')
    paginator = Paginator(valid_preprint_files, 500)
    serialize = functools.partial(search.update_file, index=index)
    for page_number in paginator.page_range:
        logger.info('Updating page {} / {}'.format(page_number, paginator.num_pages))
        search.bulk_update_nodes(serialize, paginator.page(page_number).object_list, index=index, category='file')

def migrate_groups(index, delete):
    logger.info('Migrating groups to index: {}'.format(index))
    groups = OSFGroup.objects.order_by('-id')
    increment = 100
    paginator = Paginator(groups, increment)
    for page_number in paginator.page_range:
        logger.info('Updating page {} / {}'.format(page_number, paginator.num_pages))
        OSFGroup.bulk_update_search(paginator.page(page_number).object_list, index=index)

def migrate_wikis(index, delete):
    logger.info('Migrating wiki pages to index: {}'.format(index))
    wikis = WikiPage.objects.order_by('-id')
    increment = 100
    paginator = Paginator(wikis, increment)
    for page_number in paginator.page_range:
        logger.info('Updating page {} / {}'.format(page_number, paginator.num_pages))
        search.bulk_update_wikis(paginator.page(page_number).object_list, index=index)
    logger.info('{} wikis migrated'.format(wikis.count()))

def migrate_comments(index, delete):
    logger.info('Migrating comments to index: {}'.format(index))
    comments = Comment.objects.order_by('-id')
    increment = 100
    paginator = Paginator(comments, increment)
    for page_number in paginator.page_range:
        logger.info('Updating page {} / {}'.format(page_number, paginator.num_pages))
        search.bulk_update_comments(paginator.page(page_number).object_list, index=index)
    logger.info('{} comments migrated'.format(comments.count()))

def migrate_files(index, delete, increment=10000):
    logger.info('Migrating files to index: {}'.format(index))
    last = BaseFileNode.objects.last()
    if last is None:
        logger.info('0 file migrated')
        return
    max_fid = last.id
    total_files = sql_migrate(
        index,
        JSON_UPDATE_FILES_SQL,
        max_fid,
        increment,
        spam_flagged_removed_from_search=settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH)
    logger.info('{} files migrated'.format(total_files))
    if delete:
        logger.info('Preparing to delete old file documents')
        max_fid = BaseFileNode.objects.last().id
        total_files = sql_migrate(
            index,
            JSON_DELETE_FILES_SQL,
            max_fid,
            increment,
            es_args={'raise_on_error': False},  # ignore 404s
            spam_flagged_removed_from_search=settings.SPAM_FLAGGED_REMOVE_FROM_SEARCH)
        logger.info('{} files marked deleted'.format(total_files))

def migrate_users(index, delete, increment=10000):
    logger.info('Migrating users to index: {}'.format(index))
    last = OSFUser.objects.last()
    if last is None:
        logger.info('0 user migrated')
        return
    max_uid = last.id
    total_users = sql_migrate(
        index,
        JSON_UPDATE_USERS_SQL,
        max_uid,
        increment)
    logger.info('{} users migrated'.format(total_users))
    if delete:
        logger.info('Preparing to delete old user documents')
        max_uid = OSFUser.objects.last().id
        total_users = sql_migrate(
            index,
            JSON_DELETE_USERS_SQL,
            max_uid,
            increment,
            es_args={'raise_on_error': False})  # ignore 404s
        logger.info('{} users marked deleted'.format(total_users))

def migrate_collected_metadata(index, delete):
    cgms = CollectionSubmission.objects.filter(
        collection__provider__isnull=False,
        collection__is_public=True,
        collection__deleted__isnull=True,
        collection__is_bookmark_collection=False)

    docs = helpers.scan(es_client(), query={
        'query': {'match': {'_type': 'collectionSubmission'}}
    }, index=index)

    actions = ({
        '_op_type': 'delete',
        '_index': index,
        '_id': doc['_source']['id'],
        '_type': 'collectionSubmission',
        'doc': doc['_source'],
        'doc_as_upsert': True,
    } for doc in list(docs))

    bulk_update_cgm(None, actions=actions, op='delete', index=index)

    bulk_update_collected_metadata(cgms, index=index)
    logger.info('{} collection submissions migrated'.format(cgms.count()))

def migrate_institutions(index):
    for inst in Institution.objects.filter(is_deleted=False):
        update_institution(inst, index)

def migrate(delete, remove=False, remove_all=False, index=None, app=None):
    """Reindexes relevant documents in ES

    :param bool delete: Delete documents that should not be indexed
    :param bool remove: Removes old index after migrating
    :param str index: index alias to version and migrate
    :param App app: Flask app for context
    """
    index = es_index(index)
    app = app or init_app('website.settings', set_backends=True, routes=True)

    script_utils.add_file_logger(logger, __file__)
    # NOTE: We do NOT use the app.text_request_context() as a
    # context manager because we don't want the teardown_request
    # functions to be triggered
    ctx = app.test_request_context()
    ctx.push()

    new_index = set_up_index(index)

    if settings.ENABLE_INSTITUTIONS:
        migrate_institutions(new_index)
    migrate_nodes(new_index, delete=delete)
    migrate_files(new_index, delete=delete)
    migrate_wikis(new_index, delete=delete)
    migrate_comments(new_index, delete=delete)
    migrate_users(new_index, delete=delete)
    migrate_preprints(new_index, delete=delete)
    migrate_preprint_files(new_index, delete=delete)
    migrate_collected_metadata(new_index, delete=delete)
    migrate_groups(new_index, delete=delete)

    set_up_alias(index, new_index)

    if remove:
        remove_old_index(new_index)
    if remove_all:
        remove_all_old_index(new_index)

    ctx.pop()

def set_up_index(idx):
    try:
        alias = es_client().indices.get_aliases(index=idx)
    except Exception:
        alias = None

    if not alias or not alias.keys() or idx in alias.keys():
        # Deal with empty indices or the first migration
        index = '{}_v1'.format(idx)
        search.create_index(index=index)
        logger.info('Reindexing {0} to {1}_v1'.format(idx, idx))
        es_client().indices.create(index=idx, ignore=[400])  # HTTP 400 if index already exists
        helpers.reindex(es_client(), idx, index)
        logger.info('Deleting {} index'.format(idx))
        es_client().indices.delete(index=idx)
        es_client().indices.put_alias(index=index, name=idx)
    else:
        # Increment version
        version = int(alias.keys()[0].split('_v')[1]) + 1
        logger.info('Incrementing index version to {}'.format(version))
        index = '{0}_v{1}'.format(idx, version)
        es_client().indices.delete(index=index, ignore=404)
        search.create_index(index=index)
        logger.info('{} index created'.format(index))
    return index


def set_up_alias(old_index, index):
    alias = es_client().indices.get_aliases(index=old_index)
    if alias:
        logger.info('Removing old aliases to {}'.format(old_index))
        es_client().indices.delete_alias(index=old_index, name='_all', ignore=404)
    logger.info('Creating new alias from {0} to {1}'.format(old_index, index))
    es_client().indices.put_alias(index=index, name=old_index)


def remove_old_index(index):
    logger.info('remove_old_index: {}'.format(index))
    old_version = int(index.split('_v')[1]) - 1
    if old_version < 1:
        logger.info('No index before {} to delete'.format(index))
        pass
    else:
        old_index = index.split('_v')[0] + '_v' + str(old_version)
        logger.info('Deleting {}'.format(old_index))
        es_client().indices.delete(index=old_index, ignore=404)

def remove_all_old_index(index):
    logger.info('remove_all_old_index: {}'.format(index))
    old_version = int(index.split('_v')[1]) - 1
    for v in range(1, old_version + 1):
        old_index = index.split('_v')[0] + '_v' + str(v)
        logger.info('Deleting {}'.format(old_index))
        es_client().indices.delete(index=old_index, ignore=404)

if __name__ == '__main__':
    migrate(False)
