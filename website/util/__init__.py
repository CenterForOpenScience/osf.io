# -*- coding: utf-8 -*-
from flask import url_for, request


def api_url_for(view_name, *args, **kwargs):
    return url_for(
        'JSONRenderer__{0}'.format(view_name),
        *args, **kwargs
    )


def web_url_for(view_name, *args, **kwargs):
    return url_for(
        'OsfWebRenderer__{0}'.format(view_name),
        *args, **kwargs
    )


def is_json_request():
    """Return True if the current request is a JSON/AJAX request."""
    return request.content_type == 'application/json'
