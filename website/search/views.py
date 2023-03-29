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
from website import settings
from website.project.views.contributor import get_node_contributors_abbrev
from website.ember_osf_web.decorators import ember_flag_is_active
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


@ember_flag_is_active(features.EMBER_SEARCH_PAGE)
def search_view():
    return {'shareUrl': settings.SHARE_URL}


@collect_auth
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
