import website.settings

from flask import Flask, request, jsonify, render_template, \
    render_template_string, Blueprint, send_file, abort, make_response, \
    redirect, url_for, send_from_directory

from werkzeug.utils import secure_filename

import os


app = Flask(
    __name__,
    static_folder=os.path.abspath("website/static"),
    static_url_path="/static"
)


route = app.route


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


def getReferrer():
    return request.referrer