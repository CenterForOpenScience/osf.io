# -*- coding: utf-8 -*-
import time
import logging
import functools
import httplib as http

import bleach

from flask import request

from modularodm import Q

from framework.auth.decorators import collect_auth
from framework.auth.decorators import must_be_logged_in

from website.models import Node
from website.models import User
from website.search import exceptions
import website.search.search as search
from framework.exceptions import HTTPError
from website.search.util import build_query
from website.project.views.contributor import get_node_contributors_abbrev

logger = logging.getLogger(__name__)


def handle_search_errors(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exceptions.MalformedQueryError:
            raise HTTPError(http.BAD_REQUEST, data={
                'message_short': 'Bad search query',
                'message_long': ('Please check our help (the question mark beside the search box) for more information '
                                 'on advanced search queries.'),
            })
        except exceptions.SearchUnavailableError:
            raise HTTPError(http.SERVICE_UNAVAILABLE, data={
                'message_short': 'Search unavailable',
                'message_long': ('Our search service is currently unavailable, if the issue persists, '
                'please report it to <a href="mailto:support@osf.io">support@osf.io</a>.'),
            })
    return wrapped


@handle_search_errors
def search_search(**kwargs):
    _type = kwargs.get('type', None)

    tick = time.time()
    results = {}

    if request.method == 'POST':
        results = search.search(request.get_json(), doc_type=_type)
    elif request.method == 'GET':
        q = request.args.get('q', '*')
        # TODO Match javascript params?
        start = request.args.get('from', '0')
        size = request.args.get('size', '10')
        results = search.search(build_query(q, start, size), doc_type=_type)

    results['time'] = round(time.time() - tick, 2)
    return results


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
    # TODO(fabianvf): At some point, it would be nice to do this with elastic search
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
        Q('category', 'eq', category)  # is a project
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

        out.append({
            'id': project._id,
            'label': project.title,
            'value': project.title,
            'category': 'My Projects' if user in project.contributors else 'Public Projects',
            'authors': authors_html,
        })

    return out


@collect_auth
def search_contributor(auth):
    user = auth.user if auth else None
    nid = request.args.get('excludeNode')
    exclude = Node.load(nid).contributors if nid else []
    query = bleach.clean(request.args.get('query', ''), tags=[], strip=True)
    page = int(bleach.clean(request.args.get('page', '0'), tags=[], strip=True))
    size = int(bleach.clean(request.args.get('size', '5'), tags=[], strip=True))
    return search.search_contributor(query=query, page=page, size=size,
                                     exclude=exclude, current_user=user)
