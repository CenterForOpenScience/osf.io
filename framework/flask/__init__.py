# -*- coding: utf-8 -*-
from flask import (Flask, request, jsonify, render_template,  # noqa
    render_template_string, Blueprint, send_file, abort, make_response,
    redirect as flask_redirect, url_for, send_from_directory, current_app
)
import furl
from flask_babel import Babel
from flask_compress import Compress

from website import settings

# Create app
app = Flask(
    __name__,
    static_folder=settings.STATIC_FOLDER,
    static_url_path=settings.STATIC_URL_PATH,
)
Compress(app)

# Pull debug mode from settings
app.debug = settings.DEBUG_MODE
app.config['SENTRY_TAGS'] = {'App': 'web'}
app.config['SENTRY_RELEASE'] = settings.VERSION

app.config['BABEL_TRANSLATION_DIRECTORIES'] = settings.BABEL_TRANSLATION_DIRECTORIES
app.config['BABEL_DOMAIN'] = settings.BABEL_DOMAIN
app.config['BABEL_DEFAULT_LOCALE'] = settings.BABEL_DEFAULT_LOCALE
babel = Babel(app)

@babel.localeselector
def get_locale():
    return request.accept_languages.best_match(settings.BABEL_LANGUAGES.keys())

def rm_handler(app, handler_name, func, key=None):
    """Remove a handler from an application.
    :param app: Flask app
    :param handler_name: Name of handler type, e.g. 'before_request'
    :param func: Handler function to attach
    :param key: Blueprint name
    """
    handler_funcs_name = '{0}_funcs'.format(handler_name)
    handler_funcs = getattr(app, handler_funcs_name)
    try:
        handler_funcs.get(key, []).remove(func)
    except ValueError:
        pass

def rm_handlers(app, handlers, key=None):
    """Remove multiple handlers from an application.

    :param app: Flask application
    :param handlers: Mapping from handler names to handler functions
    """
    for handler_name, func in handlers.items():
        rm_handler(app, handler_name, func, key=key)


# Set up static routing for addons
def add_handler(app, handler_name, func, key=None):
    """Add handler to Flask application if handler has not already been added.
    Used to avoid attaching the same handlers more than once, e.g. when setting
    up multiple applications during testing.

    :param app: Flask app
    :param handler_name: Name of handler type, e.g. 'before_request'
    :param func: Handler function to attach
    :param key: Blueprint name

    """
    handler_adder = getattr(app, handler_name)
    handler_funcs_name = '{0}_funcs'.format(handler_name)
    handler_funcs = getattr(app, handler_funcs_name)
    if func not in handler_funcs.get(key, []):
        handler_adder(func)


def add_handlers(app, handlers, key=None):
    """Add multiple handlers to application.

    :param app: Flask application
    :param handlers: Mapping from handler names to handler functions

    """
    for handler_name, func in handlers.items():
        add_handler(app, handler_name, func, key=key)

def redirect(location, code=302):
    """Redirect the client to a desired location. Behaves the same
    as Flask's :func:`flask.redirect` function with an awareness of
    OSF view-only links.

    IMPORTANT: This function should always be used instead of
    flask.redirect to ensure the correct behavior of view-only
    links.
    """
    view_only = request.args.get('view_only', '')
    if view_only:
        url = furl.furl(location)
        url.args['view_only'] = view_only
        location = url.url
    return flask_redirect(location, code=code)
