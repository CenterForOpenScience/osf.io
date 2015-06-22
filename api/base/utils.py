# -*- coding: utf-8 -*-

import furl

from rest_framework.exceptions import NotFound
from rest_framework.reverse import reverse
from modularodm.exceptions import NoResultsFound
from modularodm import Q

from api.base import settings as api_settings
from website import settings as website_settings
from website import util as website_util  # noqa


def absolute_reverse(view_name, query_kwargs=None, args=None, kwargs=None):
    """Like django's `reverse`, except returns an absolute URL. Also add query parameters."""

    # helps for creating fake components
    if kwargs is not None:
        if 'node_id' in kwargs:
            if kwargs['node_id'] == '':  # TODO This doesn't seem like a safe way to do this...(how to set
                                         # TODO node_id in kwargs?, or how to pass 'is_fake_component' to kwargs?)
                return ''

    relative_url = reverse(view_name, kwargs=kwargs)

    url = website_util.api_v2_url(relative_url, params=query_kwargs,
                                  base_prefix=api_settings.API_PATH)
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
