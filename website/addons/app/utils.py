# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

import json
import logging
from datetime import datetime
from datetime import timedelta
from cStringIO import StringIO

from dateutil.parser import parse

import PyRSS2Gen as pyrss

from werkzeug.contrib.atom import AtomFeed

from resync.resource import Resource
from resync.change_list import ChangeList
from resync.resource_list import ResourceList
from resync.capability_list import CapabilityList
from resync.resource_list import ResourceListDupeError

from website.util import rss
from website.addons.app.types import TYPE_MAP
from website.addons.app.exceptions import KeyMissMatchError
from website.addons.app.exceptions import InvalidSchemaError
from website.addons.app.exceptions import SchemaViolationError


logger = logging.getLogger(__name__)


def args_to_query(query, start=0, size=250):
    try:
        size = abs(int(size))
    except (ValueError, TypeError):
        size = 250

    try:
        start = abs(int(start))
    except (ValueError, TypeError):
        start = 0

    if size > 1000:
        size = 1000

    return {
        'query': {
            'query_string': {
                'default_field': '_all',
                'query': query,
                'analyze_wildcard': True,
                'lenient': True,
            }
        },
        'sort': [{
            'dateUpdated': {
                'order': 'desc'
            }
        }],
        'from': start,
        'size': size,
    }


def elastic_to_atom(name, data, query, url):
    if query == '*':
        title_query = 'All'
    else:
        title_query = query

    if name == 'scrapi':
        name = 'SHARE Notification Service'

    feed = AtomFeed(title='{name}: RSS for query: "{title_query}"'.format(name=name, title_query=title_query),
                    feed_url='{url}'.format(url=url),
                    author="COS")

    for doc in data:
        feed.add(
            title=doc.get('title', 'No title provided'),
            content=json.dumps(doc, indent=4, sort_keys=True),
            content_type='json',
            summary=doc.get('description', 'No summary'),
            id=doc.get('id', {}).get('serviceID') or doc['_id'],
            updated=parse(doc.get('dateUpdated')),
            link=doc['id']['url'] if doc.get('id') else doc['links'][0]['url'],
            author=format_contributors_for_atom(doc['contributors']),
            categories=format_categories(doc.get('tags')),
            published=parse(doc.get('dateCreated'))
        )

    return feed.to_string()


def format_contributors_for_atom(contributors_list):
    formatted_names = []
    for entry in contributors_list:
        formatted_names.append({
            'name': '{} {}'.format(entry['given'], entry['family']),
            'email': entry.get('email', '')
        })

    return formatted_names


def format_categories(tags_list):
    cat_list = []
    for tag in tags_list:
        cat_list.append({"term": tag})

    return cat_list


def elastic_to_rss(name, data, query, url, simple=True):
    count = len(data)

    items = [
        pyrss.RSSItem(
            guid=doc.get('id', {}).get('serviceID') or doc['_id'],
            link=doc['id']['url'] if doc.get(
                'id') else doc['links'][0]['url'],
            title=doc.get('title', 'No title provided'),
            author=doc.get('source'),
            description=doc.get('description') if simple else json.dumps(doc, indent=4, sort_keys=True),
            categories=doc.get('tags', 'No tags provided'),
            pubDate=parse(doc.get('dateUpdated'))
        )
        for doc in data
    ]

    if query == '*':
        title_query = 'All'
    else:
        title_query = query

    if name == 'scrapi':
        name = 'SHARE Notification Service'

    logger.info("{n} documents added to RSS feed".format(n=len(items)))

    rss_feed = rss.RSS2_Pshb(
        title='{name}: RSS for query: "{title_query}"'.format(name=name, title_query=title_query),
        link='{url}'.format(url=url),
        items=items,
        description='{n} results, {m} most recent displayed in feed'.format(n=count, m=len(items)),
        lastBuildDate=str(datetime.now())
    )

    f = StringIO()
    rss_feed.write_xml(f, encoding="UTF-8")

    return f.getvalue()


def elastic_to_resourcelist(name, data, q):
    ''' Returns a list of links to external resources
        resourceSync XML Document'''

    rl = ResourceList()

    for result in data:
        url = result['id']['url']
        last_mod = str(parse(result['dateUpdated']).date())
        resource = Resource(url, lastmod=last_mod)
        try:
            rl.add(resource)
        except ResourceListDupeError:
            print("Warning: duplicate URL - not adding to ResourceList")

    return rl.as_xml()


def elastic_to_changelist(name, data, q):
    ''' Returns a list of recently changed documents,
        yesterday to today '''

    # TODO - this is ineffective...
    today = datetime.today().replace(tzinfo=None)
    yesterday = today - timedelta(5)
    yesterday = yesterday.replace(tzinfo=None)

    cl = ChangeList()

    for result in data:
        url = result['id']['url']
        last_mod = parse(result['dateUpdated']).replace(tzinfo=None)

        if last_mod < today and last_mod > yesterday:
            resource = Resource(url, change='created')
            cl.add(resource)

    return cl.as_xml()


def generate_capabilitylist(changelist_url, resourcelist_url):

    cl = CapabilityList()

    cl.add(Resource(changelist_url))
    cl.add(Resource(resourcelist_url))

    return cl.as_xml()


def generate_schema(schema):
    if not isinstance(schema, dict):
        raise InvalidSchemaError('Schema must be of type dict')

    ret = {}

    try:
        for key, value in schema.items():
            if isinstance(value, dict):
                ret[key] = generate_schema(value)
            elif isinstance(value, list):
                if len(value) == 0:
                    ret[key] = list
                elif len(value) == 1:
                    ret[key] = [TYPE_MAP[value[0]]]
                else:
                    raise InvalidSchemaError(
                        'Field {} contained a list with more than one value'.format(key))
            else:
                ret[key] = TYPE_MAP[value]
    except KeyError as e:
        raise InvalidSchemaError('Invalid type {}'.format(e.message))

    return ret


def lint(data, schema, strict=False):
    if strict and data.keys != schema.keys():
        raise KeyMissMatchError()

    ret = {}

    for key, value in data.items():

        if isinstance(schema[key], dict):
            ret[key] = lint(value, schema[key], strict=strict)
        elif isinstance(schema[key], list):
            if not isinstance(value, list):
                raise SchemaViolationError('{} must be a list'.format(key))
            ret[key] = [
                schema[key][0](key, subvalue)
                for subvalue in value
            ]
        else:
            ret[key] = schema[key](key, value)

    data.update(ret)

    return data
