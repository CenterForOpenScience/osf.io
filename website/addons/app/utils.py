# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

import logging
from datetime import datetime, timedelta
from cStringIO import StringIO

from dateutil.parser import parse

import PyRSS2Gen as pyrss

from resync.resource import Resource
from resync.resource_list import ResourceList
from resync.change_list import ChangeList
from resync.capability_list import CapabilityList

from resync.resource_list import ResourceListDupeError

from website import settings
from website.util import rss


logger = logging.getLogger(__name__)


def elastic_to_rss(name, data, query, url):
    count = len(data)

    items = [
        pyrss.RSSItem(
            guid=doc.get('id',{}).get('serviceID') or doc['_id'],
            link=doc['id']['url'],
            title=doc.get('title', 'No title provided'),
            author=doc.get('source'),
            description=doc.get('description', 'No description provided'),
            categories=doc.get('tags', 'No tags provided'),
            pubDate=parse(doc.get('dateCreated'))
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
        date_updated = result['dateUpdated']
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

# def update_pubsubhubbub(application, )






