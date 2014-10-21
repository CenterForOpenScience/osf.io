# -*- coding: utf-8 -*-

from flask import make_response

from framework.exceptions import HTTPError
from framework.routing import JSONRenderer, render_mako_string

from website.util import is_json_request


def get_error_message(error):
    """Retrieve error message from error, if available.

    """
    try:
        return error.args[0]
    except IndexError:
        return ''


def handle_error(code):
    """Display an error thrown outside a routed view function.

    :param int code: Error status code
    :return: Flask `Response` object

    """
    # TODO: Remove circular import
    from website.routes import OsfWebRenderer
    json_renderer = JSONRenderer()
    web_renderer = OsfWebRenderer('', render_mako_string)

    error = HTTPError(code)
    renderer = json_renderer if is_json_request() else web_renderer
    return make_response(renderer.handle_error(error))
