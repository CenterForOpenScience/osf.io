from framework import *
from framework.Status import pushStatusMessage
from Site.Project import Node
from Solr_search import search_solr
import time
from urllib2 import HTTPError

import logging; logging.basicConfig(level=logging.DEBUG);
logger = logging.getLogger('Search.Routes')


@get('/search/')
def search_search():
    tick = time.time()
    # solr search results are automatically paginated. on the pages that are
    # not the first page, we pass the page number along with the url
    if 'pagination' in request.args:
        start = int(request.args.get('pagination'))
    else:
        start = 0
    query = request.args.get('q')
    # if there is not a query, tell our users to enter a search
    if query == '':
        pushStatusMessage('Enter a search!')
        return render(
            filename='search.mako', results=[], tags=[], query='')
    # if the search does not work,
    # post an error message to the user, otherwise,
    # the document, highlight,
    # and spellcheck suggestions are returned to us
    try:
        results, highlights, spellcheck_results = search_solr(query, start)
    except HTTPError:
        pushStatusMessage('Malformed query. Please try again')
        return render(
            filename='search.mako', results=[], tags=[], query='')
    # with our highlights and search result 'documents' we build the search
    # results so that it is easier for us to displa
    result_search, tags = create_result(highlights, results['docs'])
    total = results['numFound']
    return render(
        filename='search.mako', highlight=highlights,
        results=result_search, total=total, query=query,
        spellcheck=spellcheck_results, current_page=start,
        time=round(time.time()-tick, 2), tags=tags)


def create_result(highlights, results):
    """
    :param highlights: highlights are the snippets of highlighted text
    :param results:  results are the 'documents' that solr returns to us
    :return: we return the entire search result, which is a list of
    dictionaries
    """
    result_search = []
    tags = {}
    for result in results:
        container = {}
        id = result['id']
        # users are separate documents in our solr database,
        # so the logic for returning
        # those documents is different
        if 'user' in result:
            container['user'] = result['user']
            container['user_url'] = '/profile/'+result['id']
            result_search.append(container)
        # otherwise we only look for our public projects
        elif result['public']:
            container['title'] = result[id+'_title']
            container['url'] = result[id+'_url']
            contributors = []
            contributors_url = []
            # we're only going to show contributors on projects, for now
            for contributor in result[id+'_contributors']:
                contributors.append(contributor)
            for url in result[id+'_contributors_url']:
                contributors_url.append(url)
            container['contributors'] = contributors
            container['contributors_url'] = contributors_url
            # highlights will be returned as liss
            main_lit = []
            # we will create the wiki links
            main_wiki_link = ''
            # nest is for our nested nodes; i.e, materials, procedure ects
            nest = {}
            component_tags = []
            # need to keep track of visisted nodes for our tag cloud so we dont
            # miscount our fx of tags
            visited_nests = []
            for key, value in highlights[id].iteritems():
                if id in key:
                    # if wiki is in the key,
                    # we have to split on __ to build the url for the wik
                    if '__wiki' in key:
                        main_wiki_link = result[id+'_url'] + (
                            '/wiki/' + key.split('__')[1])
                    # we're only going to show
                    # the highlight if its wiki or description. title or
                    # tags is redundant information
                    if '__wiki' in key or '_description' in key:
                        main_lit = value
                # if id is not in key, we know that we have some
                # nested information to display
                elif id not in key:
                    # our first step is to get id of the
                    # node by splitting the key
                    # wiki keys are set up to include page name as well.
                    # so splitting to find
                    # the node id is different
                    if '__wiki' in key:
                        splits = key.split('__')
                        split_id = splits[0]
                        pagename = splits[1]
                    else:
                        split_id = key.split('_')[0]
                    # nodes can have contributors
                    contributors = []
                    contributors_url = []
                    lit = []
                    wiki_link = ''
                    # build our wiki link
                    if '__wiki' in key:
                        wiki_link = result[split_id+'_url'] + '/wiki/'+pagename
                    # again title and tags are
                    # redundant so only show highlight if the
                    # wiki or description are in the key
                    if '__wiki' in key or '_description' in key:
                        lit = value
                    # build our contributor list and our contributor url list
                    for contributor in result[split_id+'_contributors']:
                        contributors.append(contributor)
                    for url in result[split_id+'_contributors_url']:
                        contributors_url.append(url)
                    if result[split_id+'_public']:
                        nest[split_id] = {
                            'title': result[split_id+'_title'],
                            'url': result[split_id+'_url'],
                            'highlight': lit,
                            'wiki_link': wiki_link,
                            'contributors': contributors,
                            'contributors_url': contributors_url,
                        }
                        if split_id+'_tags' in result:
                            if split_id not in visited_nests:
                                # we've visted the node so
                                # append to our visited nests lists
                                visited_nests.append(split_id)
                                # we're going to have a
                                # list of all tags for each project.
                                # we're creating a list with no
                                # duplicates using sets
                                component_tags = component_tags + list(
                                    set(result[split_id+'_tags']) - set(
                                        component_tags))
                                # count the occurence of each tag
                                for tag in result[split_id+'_tags']:
                                    if tag not in tags.keys():
                                        tags[tag] = 1
                                    else:
                                        tags[tag] += 1
            # add the highlight to our dictionary
            if main_lit:
                container['highlight'] = main_lit
            else:
                container['highlight'] = None
            # and the link to the wiki
            container['wiki_link'] = main_wiki_link
            # and our nested information
            container['nest'] = nest
            if id+'_tags' in result.keys():
                # again using sets to create a list without duplicates
                container['tags'] = result[id+'_tags'] + list(
                    set(component_tags) - set(result[id+'_tags']))
                # and were still keeping count of tag occurence
                for tag in result[id+'_tags']:
                    if tag not in tags.keys():
                        tags[tag] = 1
                    else:
                        tags[tag] += 1
            result_search.append(container)
    return result_search, tags
