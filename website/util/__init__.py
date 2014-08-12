# -*- coding: utf-8 -*-
import framework
# Keep me: Makes rubeus importable from website.util
from . import rubeus  # noqa

from website import settings


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
    return framework.url_for('JSONRenderer__{0}'.format(view_name),
        _external=_external, _scheme=_scheme,
        *args, **kwargs)


def web_url_for(view_name, _absolute=False, *args, **kwargs):
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
    return framework.url_for('OsfWebRenderer__{0}'.format(view_name),
        _external=_external, _scheme=_scheme,
        *args, **kwargs)


def is_json_request():
    """Return True if the current request is a JSON/AJAX request."""
    content_type = framework.flask.request.content_type
    return content_type and ('application/json' in content_type)
