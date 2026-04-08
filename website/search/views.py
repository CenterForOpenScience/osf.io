import functools
from rest_framework import status as http_status
import logging
import time

from flask import request

from framework.auth.decorators import must_be_logged_in
from framework.exceptions import HTTPError
from framework import sentry
from website import language
from osf.models import OSFUser
from website.project.views.contributor import get_node_contributors_abbrev
from website.search import exceptions
import website.search.search as search
from website.search.util import build_query

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
        except exceptions.SearchException as e:
            # Interim fix for issue where ES fails with 500 in some settings- ensure exception is still logged until it can be better debugged. See OSF-4538
            sentry.log_exception(e)
            sentry.log_message('Elasticsearch returned an unexpected error response')
            # TODO: Add a test; may need to mock out the error response due to inability to reproduce error code locally
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_short': 'Could not perform search query',
                'message_long': language.SEARCH_QUERY_HELP,
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
            authors_html += f'<a href="{a.url}">{a.fullname}</a>'
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
