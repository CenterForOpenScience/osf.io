# -*- coding: utf-8 -*-

import time
import bleach
import logging
from urllib2 import HTTPError
from modularodm.storage.mongostorage import RawQuery as Q

from framework import must_be_logged_in, request, status

import website.search.search as search
from website.models import User, Node
from website.project.views.contributor import get_node_contributors_abbrev
from modularodm.storage.mongostorage import RawQuery as Q
from framework.exceptions import HTTPError
import httplib as http

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('search.routes')


def search_search():
    tick = time.time()
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
        results_search, tags, counts = search.search(query, start)
    except HTTPError:
        status.push_status_message('Malformed query. Please try again')
        return {
            'results': [],
            'tags': [],
            'query': '',
        }
    # with our highlights and search result 'documents' we build the search
    # results so that it is easier for us to display
    # Whether or not the user is searching for users
    searching_users = query.startswith("user:")
    total = counts if not isinstance(counts, dict) else counts['total']
    return {
        'highlight': [],
        'results': results_search,
        'total': total,
        'query': query,
        'spellcheck': [],
        'current_page': start,
        'time': round(time.time() - tick, 2),
        'tags': tags,
        'searching_users': searching_users,
        'counts': counts
    }


def conditionally_add_query_item(query, item, condition):
    """ Helper for the search_projects_by_title function which will add a condition to a query
    It will give an error if the proper search term is not used.
    :param query: The modular ODM query that you want to modify
    :param item:  the field to query on
    :param condition: yes, no, or either
    :return: the modified query
    """

    condition = condition.lower()

    if condition == "yes":
        return query & Q(item, 'eq', True)
    elif condition == "no":
        return query & Q(item, 'eq', False)
    elif condition == "either":
        return query

    raise HTTPError(http.BAD_REQUEST)

@must_be_logged_in
def search_projects_by_title(**kwargs):
    """ Search for nodes by title. Can pass in arguments from the URL to modify the search
    :arg term: The substring of the title.
    :arg category: Category of the node.
    :arg isDeleted: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg isFolder: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg isRegistration: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg includePublic: yes or no. Whether the projects listed should include public projects.
    :arg includeContributed: yes or no. Whether the search should include projects the current user has
        contributed to.
    :arg ignoreNode: a list of nodes that should not be included in the search.
    :return: a list of dictionaries of projects

    """
    #TODO(fabianvf): At some point, it would be nice to do this with elastic search
    user = kwargs['auth'].user

    term = request.args.get('term', '')
    max_results = int(request.args.get('maxResults', '10'))
    category = request.args.get('category', 'project').lower()
    is_deleted = request.args.get('isDeleted', 'no').lower()
    is_folder = request.args.get('isFolder', 'no').lower()
    is_registration = request.args.get('isRegistration', 'no').lower()
    include_public = request.args.get('includePublic', 'yes').lower()
    include_contributed = request.args.get('includeContributed', 'yes').lower()
    ignore_nodes = request.args.getlist('ignoreNode', [])

    matching_title = (
        Q('title', 'icontains', term) &  # search term (case insensitive)
        Q('category', 'eq', category)   # is a project
    )

    matching_title = conditionally_add_query_item(matching_title, 'is_deleted', is_deleted)
    matching_title = conditionally_add_query_item(matching_title, 'is_folder', is_folder)
    matching_title = conditionally_add_query_item(matching_title, 'is_registration', is_registration)

    if len(ignore_nodes) > 0:
        for node_id in ignore_nodes:
            matching_title = matching_title & Q('_id', 'ne', node_id)

    my_projects = []
    my_project_count = 0
    public_projects = []

    if include_contributed == "yes":
        my_projects = Node.find(
            matching_title &
            Q('contributors', 'contains', user._id)  # user is a contributor
        ).limit(max_results)
        my_project_count = my_project_count

    if my_project_count < max_results and include_public == "yes":
        public_projects = Node.find(
            matching_title &
            Q('is_public', 'eq', True)  # is public
        ).limit(max_results - my_project_count)

    results = list(my_projects) + list(public_projects)
    out = process_project_search_results(results, **kwargs)
    return out


@must_be_logged_in
def process_project_search_results(results, **kwargs):
    """
    :param results: list of projects from the modular ODM search
    :return: we return the entire search result, which is a list of
    dictionaries. This includes the list of contributors.
    """
    user = kwargs['auth'].user

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


def search_contributor():
    nid = request.args.get('excludeNode')
    exclude = Node.load(nid).contributors if nid else list()
    query = bleach.clean(request.args.get('query', ''), tags=[], strip=True)
    return search.search_contributor(query, exclude)
