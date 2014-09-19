

from website import settings
from website.search import search

from datetime import date


from resync.resource import Resource
from resync.resource_list import ResourceList
from resync.change_list import ChangeList
from resync.capability_list import CapabilityList


@search.requires_search
def gen_resourcelist(): 
    ''' Returns a list of all projects in the current OSF as a
        resourceSync XML Document'''

    raw_query = ''
    results = search.get_recent_documents(raw_query, start=0, size=100)
    all_results = search.get_recent_documents(raw_query, start=0, size=results['count'])

    rl = ResourceList()

    for result in all_results['results']:
        url = settings.DOMAIN + result.get('url')[1:],
        resource = Resource(url)
        rl.add(resource)

    for item in rl:
        item.uri = item.uri[0]

    return rl.as_xml()
