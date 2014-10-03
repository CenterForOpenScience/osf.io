import logging
import datetime
from cStringIO import StringIO

import PyRSS2Gen as pyrss

from website import settings
from website.search import search

logger = logging.getLogger(__name__)


@search.requires_search
def gen_rss_feed(raw_query):
    results = search.get_recent_documents(raw_query, start=0, size=100)
    logger.info('{n} results returned from search'.format(n=len(results['results'])))
    xml = dict_to_rss(results['results'], results['count'], raw_query)
    return xml


def dict_to_rss(results, count, query):
    if not query:
        query = '*'
    docs = results

    items = [
        pyrss.RSSItem(
            title=doc.get('title').encode('ascii', 'ignore'),
            link=settings.DOMAIN + doc.get('url')[1:],
            description=doc.get('description', 'No description provided'),
            guid=doc.get('id'),
            author='; '.join([contributor.encode('ascii', 'ignore') for contributor in doc.get('contributors')]) or 'No contributors listed',
            pubDate=doc.get('iso_timestamp')
        ) for doc in docs
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
