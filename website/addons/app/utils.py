# -*- coding: utf-8 -*-
"""Utility functions for the Application add-on.
"""
from __future__ import unicode_literals

import logging

import PyRSS2Gen as pyrss

from framework.guid.model import Metadata

from website import settings
from website.search import search


def create_orphaned_metadata(node_addon, report):
    metastore = Metadata(app=node_addon)
    metastore.update(report)
    metastore.system_data['is_orphan'] = True
    metastore.system_data['guid'] = metastore._id
    metastore.save()

    search.update_metadata(metastore)

    return metastore


def elastic_to_rss(data):
    items = [
        pyrss.RSSItem(
            title=doc.get('title', 'No Title'),
            link=settings.DOMAIN + doc['guid'],
            description=doc.get('description', 'No description provided'),
            guid=doc.get('id'),
            author='; '.join([contributor for contributor in doc.get('contributors')]) or 'No contributors listed',
            pubDate=doc.get('iso_timestamp')
        )
        for doc in data.values()
    ]

    logger.info("{n} documents added to RSS feed".format(n=len(items)))

    rss = pyrss.RSS2(
        title='scrAPI: RSS feed for documents retrieved from query: "{query}"'.format(query=query),
        link='{base_url}rss?q={query}'.format(base_url=settings.DOMAIN, query=query),
        items=items,
        description='{n} results, {m} most recent displayed in feed'.format(n=count, m=len(items)),
        lastBuildDate=str(datetime.datetime.now()),
    )

    f = StringIO()
    rss.write_xml(f)

    return f.getvalue()
