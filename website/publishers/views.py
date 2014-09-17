# -*- coding: utf-8 -*-

import bleach
import logging

from resync.resource import Resource
from resync.resource_list import ResourceList
from resync.change_list import ChangeList
from resync.capability_list import CapabilityList

from website.publishers import rss

from framework.flask import request

logger = logging.getLogger(__name__)


def recent_rss():
    # search results are automatically paginated. on the pages that are
    # not the first page, we pass the page number along with the url
    start = request.args.get('pagination', 0)
    try:
        start = int(start)
    except (TypeError, ValueError):
        logger.error(u'Invalid pagination value: {0}'.format(start))
        start = 0
    query = request.args.get('q')
    query = bleach.clean(query, tags=[], strip=True)

    feed = rss.gen_rss_feed(query)

    return feed


def gen_resourcelist(): 
    ''' Right now this only returns the most recent 100 
    scrapi results, but could be modified if I knew better
    how ... '''

    results, count = get_scrapi_resources('')

    rl = ResourceList()

    for result in results:
        location = result.get('location')[0]
        url = 'http://' + settings.URL + '/' + location,
        resource = Resource(url)
        rl.add(resource)

    for item in rl:
        item.uri = item.uri[0]

    return rl.as_xml()