# -*- coding: utf-8 -*-
import functools
from rest_framework import status as http_status
import logging
import time

import bleach
from django.db.models import Q
from flask import request

from framework.auth.decorators import collect_auth
from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from framework import sentry
from website import language
from osf import features
from osf.models import OSFUser, AbstractNode
from osf.models.session import Session
from website import settings
from website.project.views.contributor import get_node_contributors_abbrev
from website.ember_osf_web.decorators import ember_flag_is_active
from website.search import exceptions
import website.search.search as search
from website.search.util import build_query, build_private_search_query

logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 250


def handle_search_errors(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exceptions.MalformedQueryError:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Bad search query',
                'message_long': language.SEARCH_QUERY_HELP,
            })
        except exceptions.SearchUnavailableError:
            raise HTTPError(http_status.HTTP_503_SERVICE_UNAVAILABLE, data={
                'message_short': 'Search unavailable',
                'message_long': ('Our search service is currently unavailable, if the issue persists, '
                                 + language.SUPPORT_LINK),
            })
        except exceptions.SearchException:
            # Interim fix for issue where ES fails with 500 in some settings- ensure exception is still logged until it can be better debugged. See OSF-4538
            sentry.log_exception()
            sentry.log_message('Elasticsearch returned an unexpected error response')
            # TODO: Add a test; may need to mock out the error response due to inability to reproduce error code locally
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Could not perform search query',
                'message_long': language.SEARCH_QUERY_HELP,
            })
    return wrapped


SEARCH_API_VENDOR = 'grdm'
SEARCH_API_VERSION_1 = 1
SEARCH_API_VERSION_2 = 2  # supports 'wiki' and 'comment'

SUPPORTED_VERSIONS = {SEARCH_API_VERSION_1, SEARCH_API_VERSION_2}

def IS_SUPPORTED(version, vendor):
    return version in SUPPORTED_VERSIONS and vendor == SEARCH_API_VENDOR

def toint(obj):
    try:
        return int(obj)
    except Exception:
        return None

@handle_search_errors
@collect_auth
def search_search(**kwargs):
    _type = kwargs.get('type', None)
    auth = kwargs.get('auth', None)
    raw = kwargs.get('raw', False)

    if raw and not settings.DEBUG_MODE:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    tick = time.time()

    if settings.ENABLE_PRIVATE_SEARCH:
        results = _private_search(_type, auth, raw=raw)
    else:
        results = _default_search(_type)

    results['time'] = round(time.time() - tick, 2)
    return results


@handle_search_errors
@collect_auth
def search_search_raw(**kwargs):
    kwargs.update({'raw': True})
    return search_search(**kwargs)


def get_user_session(user):
    user_session = Session.objects.filter(
        data__auth_user_id=user._id
    ).order_by(
        '-modified'
    ).first()
    if user_session and user_session.data:
        return user_session
    return None


def _private_search(doc_type, auth, raw=False):
    results = {}

    if not auth or not auth.logged_in:
        raise HTTPError(http_status.HTTP_401_UNAUTHORIZED)
    user = auth.user

    qs = None
    if request.method == 'POST':
        # Since the scope of the renovation of a new API is widened,
        # for the time being, only the query string is extracted from
        # the JSON that came from the client, and the search query is
        # reassembled on the server side.
        json = request.get_json()
        api_ver = json.get('api_version', None)
        if api_ver:
            version = toint(api_ver.get('version', None))
            vendor = api_ver.get('vendor', None)
        else:
            version = None
            vendor = None

        if not IS_SUPPORTED(version, vendor):
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'api_version field is invalid',
                'message_long': 'api_version field is invalid'
            })
        es_dsl = json['elasticsearch_dsl']
        qs = es_dsl['query']['filtered']['query']['query_string']['query']
        start = es_dsl['from']
        size = es_dsl['size']
        sort = json.get('sort', None)
        highlight = json.get('highlight', None)
    elif request.method == 'GET':
        version = toint(request.args.get('version', None))
        vendor = request.args.get('vendor', None)
        if not IS_SUPPORTED(version, vendor):
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'version or vendor parameter is invalid',
                'message_long': 'version or vendor parameter is invalid'
            })
        qs = request.args.get('q', '*')
        # TODO Match javascript params?
        start = request.args.get('from', '0')
        size = request.args.get('size', '10')
        sort = request.args.get('sort', None)
        highlight = request.args.get('highlight', None)

    if qs is not None:
        ext = False
        if version == SEARCH_API_VERSION_2:
            ext = True  # include extended doc_types
        try:
            es_dsl = build_private_search_query(user, qs, start, size, sort, highlight)
        except Exception as e:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': str(e),
                'message_long': str(e)
            })
        results = search.search(es_dsl, doc_type=doc_type,
                                private=True, ext=ext, raw=raw)

    user_session = get_user_session(user)
    if user_session:
        try:
            size = int(size)
        except Exception:
            size = None
        user_session.data['search_size'] = size
        user_session.data['search_sort'] = sort
        user_session.save()

    return results

def _default_search(doc_type):
    results = {}
    if request.method == 'POST':
        results = search.search(request.get_json(), doc_type=doc_type)
    elif request.method == 'GET':
        q = request.args.get('q', '*')
        # TODO Match javascript params?
        start = request.args.get('from', '0')
        size = request.args.get('size', '10')
        results = search.search(build_query(q, start, size), doc_type=doc_type)
    return results


def must_be_logged_in_for_private_search(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if settings.ENABLE_PRIVATE_SEARCH:
            return must_be_logged_in(func)(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapped

@ember_flag_is_active(features.EMBER_SEARCH_PAGE)
@must_be_logged_in_for_private_search
def search_view(**kwargs):
    return search_view_base(**kwargs)

@ember_flag_is_active(features.EMBER_SEARCH_PAGE)
@must_be_logged_in_for_private_search
def search_view_cos(**kwargs):
    return search_view_base(**kwargs)

def search_view_base(**kwargs):
    sort = None
    size = None
    auth = kwargs.get('auth')
    if auth:
        user = auth.user
        user_session = get_user_session(user)
        if user_session:
            sort = user_session.data.get('search_sort')
            size = user_session.data.get('search_size')
    return {
        'shareUrl': settings.SHARE_URL,
        'search_sort': sort,
        'search_size': size,
    },

def conditionally_add_query_item(query, item, condition, value):
    """ Helper for the search_projects_by_title function which will add a condition to a query
    It will give an error if the proper search term is not used.
    :param query: The modular ODM query that you want to modify
    :param item:  the field to query on
    :param condition: yes, no, or either
    :return: the modified query
    """

    condition = condition.lower()

    if condition == 'yes':
        return query & Q(**{item: value})
    elif condition == 'no':
        return query & ~Q(**{item: value})
    elif condition == 'either':
        return query

    raise HTTPError(http_status.HTTP_400_BAD_REQUEST)


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
    is_collection = request.args.get('isFolder', 'no').lower()
    is_registration = request.args.get('isRegistration', 'no').lower()
    include_public = request.args.get('includePublic', 'yes').lower()
    include_contributed = request.args.get('includeContributed', 'yes').lower()
    ignore_nodes = request.args.getlist('ignoreNode', [])

    matching_title = Q(
        title__icontains=term,  # search term (case insensitive)
        category=category  # is a project
    )

    matching_title = conditionally_add_query_item(matching_title, 'is_deleted', is_deleted, True)
    matching_title = conditionally_add_query_item(matching_title, 'type', is_registration, 'osf.registration')
    matching_title = conditionally_add_query_item(matching_title, 'type', is_collection, 'osf.collection')

    if len(ignore_nodes) > 0:
        for node_id in ignore_nodes:
            matching_title = matching_title & ~Q(_id=node_id)

    my_projects = []
    my_project_count = 0
    public_projects = []

    if include_contributed == 'yes':
        my_projects = AbstractNode.objects.filter(
            matching_title &
            Q(_contributors=user)  # user is a contributor
        )[:max_results]
        my_project_count = my_project_count

    if my_project_count < max_results and include_public == 'yes':
        public_projects = AbstractNode.objects.filter(
            matching_title &
            Q(is_public=True)  # is public
        )[:max_results - my_project_count]

    results = list(my_projects) + list(public_projects)
    ret = process_project_search_results(results, **kwargs)
    return ret


@must_be_logged_in
def process_project_search_results(results, **kwargs):
    """
    :param results: list of projects from the modular ODM search
    :return: we return the entire search result, which is a list of
    dictionaries. This includes the list of contributors.
    """
    user = kwargs['auth'].user

    ret = []

    for project in results:
        authors = get_node_contributors_abbrev(project=project, auth=kwargs['auth'])
        authors_html = ''
        for author in authors['contributors']:
            a = OSFUser.load(author['user_id'])
            authors_html += '<a href="%s">%s</a>' % (a.url, a.fullname)
            authors_html += author['separator'] + ' '
        authors_html += ' ' + authors['others_count']

        ret.append({
            'id': project._id,
            'label': project.title,
            'value': project.title,
            'category': 'My Projects' if user in project.contributors else 'Public Projects',
            'authors': authors_html,
        })

    return ret


@must_be_logged_in
def search_contributor(auth):
    user = auth.user if auth else None
    nid = request.args.get('excludeNode')
    exclude = AbstractNode.load(nid).contributors if nid else []
    # TODO: Determine whether bleach is appropriate for ES payload. Also, inconsistent with website.sanitize.util.strip_html
    query = bleach.clean(request.args.get('query', ''), tags=[], strip=True)
    page = int(bleach.clean(request.args.get('page', '0'), tags=[], strip=True))
    size = int(bleach.clean(request.args.get('size', '5'), tags=[], strip=True))
    return search.search_contributor(query=query, page=page, size=size,
                                     exclude=exclude, current_user=user)
