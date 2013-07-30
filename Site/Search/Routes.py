from framework import *
from Site.Project import Node
from Solr_search import search_solr, search_solr_advanced
import time



import logging; logging.basicConfig(level=logging.DEBUG);
logger = logging.getLogger('Search.Routes')

@get('/search/')
def search_search():
    tick = time.time()
    query = request.args.get('q')
    results, highlights, spellcheck_results = search_solr(query)
    result_search = create_result (highlights, results['docs'])
    print result_search
    return render(filename='search.mako', highlight=highlights, results=result_search, total=results['numFound'], query=query, spellcheck=spellcheck_results, time=round(time.time()-tick, 2))

def trim(results):
    filtered_results = []
    lst_results = []
    for result in results:
        if filtered_results and len(result['url_list']) > len(filtered_results[-1]['url_list']):
            lst_results.append(result)
            continue
        filtered_results.append(result)
    lst_result = resort(lst_results)
    print lst_result
    return lst_results

def resort(lst_results):
    return sorted(lst_results, key= lambda result: result['score'], reverse=True)

def create_result(highlights, results):
    result_search = []
    print results
    for result in results:
        container = {}
        id = result['id']
        container['title'] = result[id+'_title']
        container['url'] = result[id+'_url']
        contributors = []
        contributors_url = []
        for contributor in result['contributors']:
            contributors.append(contributor)
        for url in result['contributors_url']:
            contributors_url.append(url)
        container['contributors'] = contributors
        container['contributors_url'] = contributors_url
        lit = []
        nest = {}
        nest_lit = []
        for key,value in highlights[id].iteritems():
            if id in key and ('_wiki' in key or '_description' in key):
                lit = value[0]
                print 'i made it', value[0]
                print key
            elif 'contributors' not in key and id not in key:
                print value, 'right right', key
                split_id = key.split('_')[0]
                nest[split_id] = {
                    'title':result[split_id+'_title'],
                    'url': result[split_id+'_url'],
                    'highlight':value if ('_wiki' or '_description') in key else None,
                    'tags':result[split_id+'_tags'] if split_id+'_tags' in result else None
                }
        if lit:
            container['highlight'] = lit
        else:
            container['highlight'] = None
        container['nest'] = nest
        if id+'_tags' in result.keys():
            container['tags'] = result[id+'_tags']
        result_search.append(container)
    print 'the result is', result_search
    return result_search

