# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

import logging
from datetime import datetime
from cStringIO import StringIO

from dateutil.parser import parse

import PyRSS2Gen as pyrss

from resync.resource import Resource
from resync.resource_list import ResourceList
from resync.change_list import ChangeList
from resync.capability_list import CapabilityList

from resync.resource_list import ResourceListDupeError

from website import settings


logger = logging.getLogger(__name__)


def elastic_to_rss(name, data, query):
    count = len(data)

    items = [
        pyrss.RSSItem(
            guid=doc['id']['serviceID'],
            link=doc['id']['url'],
            title=doc.get('title', 'No title provided'),
            description=doc.get('description', 'No description provided'),
            pubDate=parse(doc.get('dateCreated'))
        )
        for doc in data
    ]

    logger.info("{n} documents added to RSS feed".format(n=len(items)))

    rss = pyrss.RSS2(
        title='{name}: RSS for query: "{query}"'.format(name=name, query=query),
        link='{base_url}rss?q={query}'.format(base_url=settings.DOMAIN, query=query),
        items=items,
        description='{n} results, {m} most recent displayed in feed'.format(n=count, m=len(items)),
        lastBuildDate=str(datetime.now()),
    )

    f = StringIO()
    rss.write_xml(f, encoding="UTF-8")

    return f.getvalue()

def elastic_to_resourcelist(name, data, q):
    ''' Returns a list of projects in the current OSF as a
        resourceSync XML Document'''

    rl = ResourceList()

    for result in data:
        url = result['id']['url'],
        resource = Resource(url)
        try:
            rl.add(resource)
        except ResourceListDupeError:
            print("AAAH")

    for item in rl:
        item.uri = item.uri[0]

    return rl.as_xml()


