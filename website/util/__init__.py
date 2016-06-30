# -*- coding: utf-8 -*-

import collections
import re
import urllib
import logging
import urlparse
from contextlib import contextmanager

import furl

from flask import request, url_for

from website import settings as website_settings
from api.base import settings as api_settings
from modularodm import Q
from modularodm.exceptions import NoResultsFound

# Keep me: Makes rubeus importable from website.util
from . import rubeus  # noqa

logger = logging.getLogger(__name__)


guid_url_node_pattern = re.compile('^/project/[a-zA-Z0-9]{5,}/node(?=/[a-zA-Z0-9]{5,})')
guid_url_project_pattern = re.compile('^/project(?=/[a-zA-Z0-9]{5,})')
guid_url_profile_pattern = re.compile('^/profile(?=/[a-zA-Z0-9]{5,})')


waterbutler_action_map = {
    'upload': 'file',
    'delete': 'file',
    'download': 'file',
    'metadata': 'data',
    'create_folder': 'file',
}


# Function courtesy of @brianjgeiger and @abought, moved from API utils
def rapply(data, func, *args, **kwargs):
    """Recursively apply a function to all values in an iterable
    :param dict | list | basestring data: iterable to apply func to
    :param function func:
    """
    if isinstance(data, collections.Mapping):
        return {
            key: rapply(value, func, *args, **kwargs)
            for key, value in data.iteritems()
        }
    elif isinstance(data, collections.Iterable) and not isinstance(data, basestring):
        desired_type = type(data)
        return desired_type(
            rapply(item, func, *args, **kwargs) for item in data
        )
    else:
        return func(data, *args, **kwargs)


def conjunct(words, conj='and'):
    words = list(words)
    num_words = len(words)
    if num_words == 0:
        return ''
    elif num_words == 1:
        return words[0]
    elif num_words == 2:
        return ' {0} '.format(conj).join(words)
    elif num_words > 2:
        return ', '.join(words[:-1]) + ', {0} {1}'.format(conj, words[-1])


def _get_guid_url_for(url):
    """URL Post-processor transforms specific `/project/<pid>` or `/project/<pid>/node/<nid>`
    urls into guid urls. Ex: `<nid>/wiki/home`.
    """
    guid_url = guid_url_node_pattern.sub('', url, count=1)
    guid_url = guid_url_project_pattern.sub('', guid_url, count=1)
    guid_url = guid_url_profile_pattern.sub('', guid_url, count=1)
    return guid_url


def api_url_for(view_name, _absolute=False, _xml=False, *args, **kwargs):
    """Reverse URL lookup for API routes (that use the JSONRenderer or XMLRenderer).
    Takes the same arguments as Flask's url_for, with the addition of
    `_absolute`, which will make an absolute URL with the correct HTTP scheme
    based on whether the app is in debug mode. The _xml flag sets the renderer to use.
    """
    renderer = 'XMLRenderer' if _xml else 'JSONRenderer'

    url = url_for('{0}__{1}'.format(renderer, view_name), *args, **kwargs)

    if _absolute:
        # We do NOT use the url_for's _external kwarg because app.config['SERVER_NAME'] alters
        # behavior in an unknown way (currently breaks tests). /sloria /jspies
        return urlparse.urljoin(website_settings.DOMAIN, url)
    return url


def api_v2_url(path_str,
               params=None,
               base_route=website_settings.API_DOMAIN,
               base_prefix=api_settings.API_BASE,
               **kwargs):
    """
    Convenience function for APIv2 usage: Concatenates parts of the absolute API url based on arguments provided

    For example: given path_str = '/nodes/abcd3/contributors/' and params {'filter[fullname]': 'bob'},
        this function would return the following on the local staging environment:
        'http://localhost:8000/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob'

    This is NOT a full lookup function. It does not verify that a route actually exists to match the path_str given.
    """
    params = params or {}  # Optional params dict for special-character param names, eg filter[fullname]

    base_url = furl.furl(base_route + base_prefix)

    base_url.path.add([x for x in path_str.split('/') if x] + [''])

    base_url.args.update(params)
    base_url.args.update(kwargs)
    return str(base_url)


def web_url_for(view_name, _absolute=False, _guid=False, *args, **kwargs):
    """Reverse URL lookup for web routes (those that use the OsfWebRenderer).
    Takes the same arguments as Flask's url_for, with the addition of
    `_absolute`, which will make an absolute URL with the correct HTTP scheme
    based on whether the app is in debug mode.
    """
    url = url_for('OsfWebRenderer__{0}'.format(view_name), *args, **kwargs)
    if _guid:
        url = _get_guid_url_for(url)

    if _absolute:
        # We do NOT use the url_for's _external kwarg because app.config['SERVER_NAME'] alters
        # behavior in an unknown way (currently breaks tests). /sloria /jspies
        return urlparse.urljoin(website_settings.DOMAIN, url)
    return url


def is_json_request():
    """Return True if the current request is a JSON/AJAX request."""
    content_type = request.content_type
    return content_type and ('application/json' in content_type)


def waterbutler_url_for(route, provider, path, node, user=None, **kwargs):
    """DEPRECATED Use waterbutler_api_url_for
    Reverse URL lookup for WaterButler routes
    :param str route: The action to preform, upload, download, delete...
    :param str provider: The name of the requested provider
    :param str path: The path of the requested file or folder
    :param Node node: The node being accessed
    :param User user: The user whos cookie will be used or None
    :param dict kwargs: Addition query parameters to be appended
    """
    url = furl.furl(website_settings.WATERBUTLER_URL)
    url.path.segments.append(waterbutler_action_map[route])

    url.args.update({
        'path': path,
        'nid': node._id,
        'provider': provider,
    })

    if user:
        url.args['cookie'] = user.get_or_create_cookie()
    elif website_settings.COOKIE_NAME in request.cookies:
        url.args['cookie'] = request.cookies[website_settings.COOKIE_NAME]

    view_only = False
    if 'view_only' in kwargs:
        view_only = kwargs.get('view_only')
    else:
        view_only = request.args.get('view_only')

    url.args['view_only'] = view_only

    url.args.update(kwargs)
    return url.url


def waterbutler_api_url_for(node_id, provider, path='/', **kwargs):
    assert path.startswith('/'), 'Path must always start with /'
    url = furl.furl(website_settings.WATERBUTLER_URL)
    segments = ['v1', 'resources', node_id, 'providers', provider] + path.split('/')[1:]
    url.path.segments.extend([urllib.quote(x.encode('utf-8')) for x in segments])
    url.args.update(kwargs)
    return url.url


@contextmanager
def disconnected_from(signal, listener):
    """Temporarily disconnect a Blinker signal."""
    signal.disconnect(listener)
    yield
    signal.connect(listener)


def check_private_key_for_anonymized_link(private_key):
    from website.project.model import PrivateLink

    is_anonymous = False
    if private_key is not None:
        try:
            link = PrivateLink.find_one(Q('key', 'eq', private_key))
        except NoResultsFound:
            link = None
        if link is not None:
            is_anonymous = link.anonymous
    return is_anonymous
