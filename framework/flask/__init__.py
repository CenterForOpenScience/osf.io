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
