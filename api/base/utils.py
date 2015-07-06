# -*- coding: utf-8 -*-

import furl

from modularodm import Q
from rest_framework.reverse import reverse
from modularodm.exceptions import NoResultsFound

from website import util as website_util  # noqa
from website import settings as website_settings
from rest_framework.exceptions import NotFound

from api.nodes.settings.defaults import NODE_ALLOWED_SUBQUERY_SETS
from api.users.settings.defaults import USER_ALLOWED_SUBQUERY_SETS


def absolute_reverse(view_name, query_kwargs=None, args=None, kwargs=None):
    """Like django's `reverse`, except returns an absolute URL. Also add query parameters."""
    relative_url = reverse(view_name, kwargs=kwargs)

    url = website_util.api_v2_url(relative_url, params=query_kwargs)
    return url


def get_object_or_404(model_cls, query_or_pk):
    if isinstance(query_or_pk, basestring):
        query = Q('_id', 'eq', query_or_pk)
    else:
        query = query_or_pk
    try:
        return model_cls.find_one(query)
    except NoResultsFound:
        raise NotFound


def process_additional_query_params(include, obj_type):
    # Checks and cuts off include value if '/' is found
    include = include.split('/')[0]
    query_params = {}

    # Processes include string into ',' separated parameters with '.' marking relationships
    for raw_parameter in include.split(','):
        if obj_type == 'node':
            allowed_keys = NODE_ALLOWED_SUBQUERY_SETS
        elif obj_type == 'user':
            allowed_keys = USER_ALLOWED_SUBQUERY_SETS
        sub_query_list = raw_parameter.split('.')
        query = {}
        for sub_query in reversed(sub_query_list):
            query = {sub_query: query}
        for sub_query_test in sub_query_list:
            try:
                allowed_keys = allowed_keys[sub_query_test]
            except:
                raise NotFound('{} is not a valid property of the Node object.'.format(query))
        query_params[sub_query_list[0]] = query[sub_query_list[0]]
    return query_params


def waterbutler_url_for(request_type, provider, path, node_id, token, obj_args=None, **query):
    """Reverse URL lookup for WaterButler routes
    :param str request_type: data or metadata
    :param str provider: The name of the requested provider
    :param str path: The path of the requested file or folder
    :param str node_id: The id of the node being accessed
    :param str token: The cookie to be used or None
    :param dict **query: Addition query parameters to be appended
    """
    url = furl.furl(website_settings.WATERBUTLER_URL)
    url.path.segments.append(request_type)

    url.args.update({
        'path': path,
        'nid': node_id,
        'provider': provider,
    })

    if token is not None:
        url.args['cookie'] = token

    if 'view_only' in obj_args:
        url.args['view_only'] = obj_args['view_only']

    url.args.update(query)
    return url.url
