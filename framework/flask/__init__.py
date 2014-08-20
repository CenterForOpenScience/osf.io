from flask import Flask, request, jsonify, render_template, \
    render_template_string, Blueprint, send_file, abort, make_response, \
    redirect, url_for, send_from_directory, current_app
from werkzeug.utils import secure_filename
from website import settings

import os

# Create app
app = Flask(
    __name__,
    static_folder=os.path.abspath("website/static"),
    static_url_path="/static",
)

# Pull debug mode from settings
app.debug = settings.DEBUG_MODE

# Set up static routing for addons
# TODO: Handle this in nginx

addon_base_path = os.path.abspath('website/addons')

@app.route('/static/addons/<addon>/<path:filename>')
def addon_static(addon, filename):
    addon_path = os.path.join(addon_base_path, addon, 'static')
    return send_from_directory(addon_path, filename)


def add_handler(app, handler_name, func):
    """Add handler to Flask application if handler has not already been added.
    Used to avoid attaching the same handlers more than once, e.g. when setting
    up multiple applications during testing.

    :param app: Flask app
    :param handler_name: Name of handler type, e.g. 'before_request'
    :param func: Handler function to attach

    """
    adder = getattr(app, handler_name)
    handlers = getattr(app, '{0}_funcs'.format(handler_name))
    if func not in handlers.get(None, []):
        adder(func)

