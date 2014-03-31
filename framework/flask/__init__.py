from flask import Flask, send_from_directory
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
