# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

import logging
from datetime import datetime
from cStringIO import StringIO

from dateutil.parser import parse

import PyRSS2Gen as pyrss

from framework.guid.model import Metadata

from website import settings
from website.search import search


logger = logging.getLogger(__name__)


def create_orphaned_metadata(node_addon, metadata):
    metastore = Metadata(app=node_addon)
    metastore.update(metadata)
    metastore.system_data['is_orphan'] = True
    metastore.system_data['guid'] = metastore._id
    metastore.save()

    search.update_metadata(metastore)

    return metastore


def elastic_to_rss(name, data, query):
    count = len(data)

    items = [
        pyrss.RSSItem(
            guid=doc['guid'],
            link='{}{}/'.format(settings.DOMAIN, doc['guid']),
            title=doc.get('title', 'No title provided'),
            description=doc.get('description', 'No description provided'),
            pubDate=parse(doc.get('timestamp'))
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
    rss.write_xml(f)

    return f.getvalue()
