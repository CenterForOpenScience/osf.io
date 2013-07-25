import website.settings

from flask import Flask, jsonify, render_template, render_template_string, Blueprint, send_file, abort
from werkzeug import secure_filename

###############################################################################

app = Flask(__name__)

def set_static_folder(static_url_path, static_folder):
    def send_static_file(filename):
        return send_from_directory(static_folder, filename)

    app.add_url_rule(static_url_path + '/<path:filename>',
        endpoint='static',
        view_func=send_static_file
    )
    return app

###############################################################################

route = app.route

###############################################################################

# https://github.com/ab3/flask/blob/5cdcbb3bcec8e2be222d1ed62dcf6151bfd05271/flask/app.py
def get(rule, **options):
    """Short for :meth:`route` with methods=['GET']) as option."""
    def decorator(f):
        options["methods"] = ('GET', 'HEAD')
        endpoint = options.pop("endpoint", None)
        app.add_url_rule(rule, endpoint, f, **options)
        return f
    return decorator


def post(rule, **options):
    """Short for :meth:`route` with methods=['POST']) as option."""
    def decorator(f):
        options["methods"] = ('POST', 'HEAD')
        endpoint = options.pop("endpoint", None)
        app.add_url_rule(rule, endpoint, f, **options)
        return f
    return decorator

###############################################################################

from flask import request, redirect, url_for, send_from_directory

###############################################################################

def getReferrer():
    return request.referrer