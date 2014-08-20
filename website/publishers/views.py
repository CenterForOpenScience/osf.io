# -*- coding: utf-8 -*-

import bleach
import logging
from urllib2 import HTTPError

from website.publishers import rss

from framework import request, status



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
    # if there is not a query, tell our users to enter a search
    query = bleach.clean(query, tags=[], strip=True)
    # if the search does not work,
    # post an error message to the user, otherwise,
    # the document, highlight,
    # and spellcheck suggestions are returned to us
    feed = rss.gen_rss_feed(query)

    return feed
