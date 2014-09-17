

from website import settings
from website.search import search

from datetime import date


from resync.resource import Resource
from resync.resource_list import ResourceList
from resync.change_list import ChangeList
from resync.capability_list import CapabilityList


@search.requires_search
def gen_resourcelist(): 
    ''' Right now this only returns the most recent 100 
    osf projects, but could be modified if I knew better
    how ... '''

    raw_query = ''
    results = search.get_recent_documents(raw_query, start=0, size=100)

    rl = ResourceList()
    # results is a dict with keys count, results
    # results['results'] is a list

    # import pdb; pdb.set_trace()

    for result in results['results']:
        url = settings.DOMAIN + result.get('url')[1:],
        resource = Resource(url)
        rl.add(resource)

    for item in rl:
        item.uri = item.uri[0]

    return rl.as_xml()

# @search.requires_search
# def gen_rss_feed(raw_query):
#     results = search.get_recent_documents(raw_query, start=0, size=100)
#     logger.info('{n} results returned from search'.format(n=len(results['results'])))
#     xml = dict_to_rss(results['results'], results['count'], raw_query)
#     return xml


# def dict_to_rss(results, count, query):
#     if not query:
#         query = '*'
#     docs = results

#     items = [
#         pyrss.RSSItem(
#             title=doc.get('title').encode('ascii', 'ignore'),
#             link=settings.DOMAIN + doc.get('url')[1:],
#             description=doc.get('description').encode('ascii', 'ignore') or 'No description provided',
#             guid=doc.get('id'),
#             author='; '.join([contributor.encode('ascii', 'ignore') for contributor in doc.get('contributors')]) or 'No contributors listed',
#             pubDate=doc.get('iso_timestamp')
#         ) for doc in docs
#     ]
#     logger.info("{n} documents added to RSS feed".format(n=len(items)))
#     rss = pyrss.RSS2(
#         title='scrAPI: RSS feed for documents retrieved from query: "{query}"'.format(query=query),
#         link='{base_url}rss?q={query}'.format(base_url=settings.DOMAIN, query=query),
#         items=items,
#         description='{n} results, {m} most recent displayed in feed'.format(n=count, m=len(items)),
#         lastBuildDate=str(datetime.datetime.now()),
#     )

#     f = StringIO()
#     rss.write_xml(f)

#     return f.getvalue()
