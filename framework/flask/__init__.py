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
