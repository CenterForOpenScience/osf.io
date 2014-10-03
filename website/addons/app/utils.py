# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

import logging
from datetime import datetime
from cStringIO import StringIO

from dateutil.parser import parse

import PyRSS2Gen as pyrss

from website import settings


logger = logging.getLogger(__name__)


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
