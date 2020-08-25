# -*- coding: utf-8 -*-

import logging
import re
from future.moves.urllib.parse import urljoin

from django.utils.http import urlencode
from flask import request, url_for

from website import settings as website_settings
from api.base import settings as api_settings

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

# Move to api utils?
def api_url_for(view_name, _absolute=False, _xml=False, _internal=False, *args, **kwargs):
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
        domain = website_settings.INTERNAL_DOMAIN if _internal else website_settings.DOMAIN
        return urljoin(domain, url)
    return url

# Move somewhere
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

    x = urljoin(base_route, urljoin(base_prefix, path_str.lstrip('/')))

    if params or kwargs:
        x = '{}?{}'.format(x, urlencode(dict(params, **kwargs)))

    return x

# Move to api utils?
def web_url_for(view_name, _absolute=False, _internal=False, _guid=False, *args, **kwargs):
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
        domain = website_settings.INTERNAL_DOMAIN if _internal else website_settings.DOMAIN
        return urljoin(domain, url)
    return url


def is_json_request():
    """Return True if the current request is a JSON/AJAX request."""
    content_type = request.content_type
    return content_type and ('application/json' in content_type)
