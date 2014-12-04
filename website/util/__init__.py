# -*- coding: utf-8 -*-

import re
from flask import request, url_for

from website import settings

# Keep me: Makes rubeus importable from website.util
from . import rubeus  # noqa


guid_url_node_pattern = re.compile('^/project/[a-zA-Z0-9]{5,}/node(?=/[a-zA-Z0-9]{5,})')
guid_url_project_pattern = re.compile('^/project(?=/[a-zA-Z0-9]{5,})')
guid_url_profile_pattern = re.compile('^/profile(?=/[a-zA-Z0-9]{5,})')


def _get_guid_url_for(url):
    """URL Post-processor transforms specific `/project/<pid>` or `/project/<pid>/node/<nid>`
    urls into guid urls. Ex: `<nid>/wiki/home`.
    """
    guid_url = guid_url_node_pattern.sub('', url, count=1)
    guid_url = guid_url_project_pattern.sub('', guid_url, count=1)
    guid_url = guid_url_profile_pattern.sub('', guid_url, count=1)
    return guid_url


def api_url_for(view_name, _absolute=False, *args, **kwargs):
    """Reverse URL lookup for API routes (those that use the JSONRenderer).
    Takes the same arguments as Flask's url_for, with the addition of
    `_absolute`, which will make an absolute URL with the correct HTTP scheme
    based on whether the app is in debug mode.
    """
    if _absolute:
        # Pop off kwargs to ensure that keyword arguments are only passed
        # once
        _external = kwargs.pop('_external', True)
        scheme = 'http' if settings.DEBUG_MODE else 'https'
        _scheme = kwargs.pop('_scheme', scheme)
    else:
        _external = kwargs.pop('_external', False)
        _scheme = kwargs.pop('_scheme', None)
    return url_for('JSONRenderer__{0}'.format(view_name),
        _external=_external, _scheme=_scheme,
        *args, **kwargs)


def web_url_for(view_name, _absolute=False, _guid=False, *args, **kwargs):
    """Reverse URL lookup for web routes (those that use the OsfWebRenderer).
    Takes the same arguments as Flask's url_for, with the addition of
    `_absolute`, which will make an absolute URL with the correct HTTP scheme
    based on whether the app is in debug mode.
    """
    if _absolute:
        _external = kwargs.pop('_external', True)
        scheme = 'http' if settings.DEBUG_MODE else 'https'
        _scheme = kwargs.pop('_scheme', scheme)
    else:
        _external = kwargs.pop('_external', False)
        _scheme = kwargs.pop('_scheme', None)
    url = url_for('OsfWebRenderer__{0}'.format(view_name),
        _external=_external, _scheme=_scheme,
        *args, **kwargs)
    if _guid:
        url = _get_guid_url_for(url)
    return url

def is_json_request():
    """Return True if the current request is a JSON/AJAX request."""
    content_type = request.content_type
    return content_type and ('application/json' in content_type)
