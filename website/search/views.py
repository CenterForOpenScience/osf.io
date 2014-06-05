import re
import time
from urllib2 import HTTPError
import logging

from framework import must_be_logged_in, request, status
from website.search.solr_search import search_solr
from website import settings
from website.filters import gravatar
from website.models import User, Node
from website.project.views.contributor import get_node_contributors_abbrev
from modularodm.storage.mongostorage import RawQuery as Q

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('search.routes')


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
        status.push_status_message('No search query', 'info')
        return {
            'results': [],
            'tags': [],
            'query': '',
        }
    # if the search does not work,
    # post an error message to the user, otherwise,
    # the document, highlight,
    # and spellcheck suggestions are returned to us
    try:
        results, highlights, spellcheck_results = search_solr(query, start)
    except HTTPError:
        status.push_status_message('Malformed query. Please try again')
        return {
            'results': [],
            'tags': [],
            'query': '',
        }
    # with our highlights and search result 'documents' we build the search
    # results so that it is easier for us to display
    result_search, tags = create_result(highlights, results['docs'])
    total = results['numFound']
    # Whether or not the user is searching for users
    searching_users = query.startswith("user:")
    return {
        'highlight': highlights,
        'results': result_search,
        'total': total,
        'query': query,
        'spellcheck': spellcheck_results,
        'current_page': start,
        'time': round(time.time() - tick, 2),
        'tags': tags,
        'searching_users': searching_users
    }


@must_be_logged_in
def search_projects_by_title(**kwargs):

    term = request.args.get('term')
    user = kwargs['auth'].user

    max_results = 10

    matching_title = (
        Q('title', 'icontains', term) &  # search term (case insensitive)
        Q('category', 'eq', 'project') &  # is a project
        Q('is_deleted', 'eq', False)  # isn't deleted
    )

    my_projects = Node.find(
        matching_title &
        Q('contributors', 'contains', user._id)  # user is a contributor
    ).limit(max_results)

    if my_projects.count() < max_results:
        public_projects = Node.find(
            matching_title &
            Q('is_public', 'eq', True)  # is public
        ).limit(max_results - my_projects.count())
    else:
        public_projects = []

    results = list(my_projects) + list(public_projects)

    out = []

    for project in results:
        authors = get_node_contributors_abbrev(project=project, auth=kwargs['auth'])
        authors_html = ''
        for author in authors['contributors']:
            a = User.load(author['user_id'])
            authors_html += '<a href="%s">%s</a>' % (a.url, a.fullname)
            authors_html += author['separator'] + ' '
        authors_html += ' ' + authors['others_count']
        if authors['others_count']:
            authors_html += ' other' + authors['others_suffix']

        out.append({
            'id': project._id,
            'label': project.title,
            'value': project.title,
            'category': 'My Projects' if user in project.contributors else 'Public Projects',
            'authors': authors_html,
        })

    return out


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
        else:
            container['title'] = result.get(id+'_title', '-- private project --')
            container['url'] = result.get(id+'_url')
            contributors = []
            contributors_url = []
            # we're only going to show contributors on projects, for now
            for contributor in result.get(id+'_contributors', []):
                contributors.append(contributor)
            for url in result.get(id+'_contributors_url', []):
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
                    if key == 'id':
                        continue
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
                        if value[0] != 'None':
                            lit = value
                    # build our contributor list and our contributor url list
                    for contributor in result.get(split_id+'_contributors', []):
                        contributors.append(contributor)
                    for url in result.get(split_id+'_contributors_url', []):
                        contributors_url.append(url)
                    if result[split_id+'_public']:
                        nest[split_id] = {
                            'title': result[split_id+'_title'],
                            'url': result[split_id+'_url'],
                            'highlight': lit or nest.get(split_id)['highlight'] if nest.get(split_id) else None,
                            'wiki_link': wiki_link,
                            'contributors': contributors,
                            'contributors_url': contributors_url
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
            container['is_registration'] = result.get(
                id + '_registeredproject',
                False
            )
            if id + '_tags' in result.keys():
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


def _search_contributor(query, exclude=None):
    """Search for contributors to add to a project using Solr. Request must
    include JSON data with a "query" field.

    :param: Search query
    :return: List of dictionaries, each containing the ID, full name, and
        gravatar URL of an OSF user

    """
    # Prepare query
    query = re.sub(r'[\-\+]', ' ', query)

    # Prepend "user:" to each token in the query; else Solr will search for
    # e.g. user:Barack AND Obama. Also search for tokens plus wildcard so that
    # Bar will match Barack. Note: in Solr, Barack* does not match Barack,
    # so must search for (Barack OR Barack*).
    q = ' AND '.join([
        u'user:({token} OR {token}*)'.format(token=token).encode('utf-8')
        for token in re.split(r'\s+', query)
    ])

    result, highlight, spellcheck_result = search_solr(q)
    docs = result.get('docs', [])

    if exclude:
        docs = (x for x in docs if x.get('id') not in exclude)

    users = []
    for doc in docs:
        # TODO: use utils.serialize_user
        user = User.load(doc['id'])
        if user is None:
            logger.error('Could not load user {0}'.format(doc['id']))
            continue
        if user.is_active():  # exclude merged, unregistered, etc.
            users.append({
                'fullname': doc['user'],
                'id': doc['id'],
                'gravatar_url': gravatar(
                    user,
                    use_ssl=True,
                    size=settings.GRAVATAR_SIZE_ADD_CONTRIBUTOR,
                ),
                'registered': user.is_registered,
                'active': user.is_active()
            })

    return {'users': users}


def search_contributor():
    nid = request.args.get('excludeNode')
    exclude = Node.load(nid).contributors if nid else list()

    return _search_contributor(
        query=request.args.get('query', ''),
        exclude=exclude,
    )
