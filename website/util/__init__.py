# -*- coding: utf-8 -*-
import framework
from . import rubeus

from website import settings



def api_url_for(view_name, _absolute=False, *args, **kwargs):
    if _absolute:
        external = True
        scheme = 'http' if settings.DEBUG_MODE else 'https'
    else:
        external = False
        scheme = None
    return framework.url_for('JSONRenderer__{0}'.format(view_name),
        _external=external, _scheme=scheme,
        *args, **kwargs)


def web_url_for(view_name, _absolute=False, *args, **kwargs):
    if _absolute:
        external = True
        scheme = 'http' if settings.DEBUG_MODE else 'https'
    else:
        external = False
        scheme = None
    return framework.url_for('OsfWebRenderer__{0}'.format(view_name),
        _external=external, _scheme=scheme,
        *args, **kwargs)


def is_json_request():
    """Return True if the current request is a JSON/AJAX request."""
    return framework.flask.request.content_type == 'application/json'
