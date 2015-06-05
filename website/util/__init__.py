# -*- coding: utf-8 -*-

import re
import logging
import urlparse

import furl

from flask import request, url_for
from django.core.urlresolvers import reverse

from website import settings

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

def _get_guid_url_for(url):
    """URL Post-processor transforms specific `/project/<pid>` or `/project/<pid>/node/<nid>`
    urls into guid urls. Ex: `<nid>/wiki/home`.
    """
    guid_url = guid_url_node_pattern.sub('', url, count=1)
    guid_url = guid_url_project_pattern.sub('', guid_url, count=1)
    guid_url = guid_url_profile_pattern.sub('', guid_url, count=1)
    return guid_url

def api_v2_url_for(*args, **kwargs):
    return reverse(prefix='/', *args, **kwargs)


def api_url_for(view_name, _absolute=False, _offload=False, _xml=False, *args, **kwargs):
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
        domain = settings.OFFLOAD_DOMAIN if _offload else settings.DOMAIN
        return urlparse.urljoin(domain, url)
    return url


def web_url_for(view_name, _absolute=False, _offload=False, _guid=False, *args, **kwargs):
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
        domain = settings.OFFLOAD_DOMAIN if _offload else settings.DOMAIN
        return urlparse.urljoin(domain, url)
    return url


def is_json_request():
    """Return True if the current request is a JSON/AJAX request."""
    content_type = request.content_type
    return content_type and ('application/json' in content_type)


def waterbutler_url_for(route, provider, path, node, user=None, **query):
    """Reverse URL lookup for WaterButler routes
    :param str route: The action to preform, upload, download, delete...
    :param str provider: The name of the requested provider
    :param str path: The path of the requested file or folder
    :param Node node: The node being accessed
    :param User user: The user whos cookie will be used or None
    :param dict **query: Addition query parameters to be appended
    """
    url = furl.furl(settings.WATERBUTLER_URL)
    url.path.segments.append(waterbutler_action_map[route])

    url.args.update({
        'path': path,
        'nid': node._id,
        'provider': provider,
    })

    if user:
        url.args['cookie'] = user.get_or_create_cookie()
    elif settings.COOKIE_NAME in request.cookies:
        url.args['cookie'] = request.cookies[settings.COOKIE_NAME]

    if 'view_only' in request.args:
        url.args['view_only'] = request.args['view_only']

    url.args.update(query)
    return url.url
