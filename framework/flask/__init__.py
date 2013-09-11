import website.settings

from flask import Flask, request, jsonify, render_template, render_template_string, Blueprint, send_file, abort, make_response, g
from werkzeug import secure_filename
from werkzeug.local import LocalProxy, Local
import itsdangerous
import bson.objectid

###############################################################################

app = Flask(__name__)

sessions = {}

def get_session():
    if hasattr(g, 'session_id'):
        try:
            return sessions[g.session_id]
        except KeyError:
            sessions[g.session_id] = {}
            return sessions[g.session_id]
    return {}

session = LocalProxy(get_session)

def set_previous_url(url=None):
    if url is None:
        url = request.referrer
    set('url_previous', url)

def goback():
    url_previous = session.get('url_previous')
    if url_previous:
        del session['url_previous']
        return redirect(url_previous)

def create_key_and_cookie():
    key = str(bson.objectid.ObjectId())
    return key, ('osf', itsdangerous.Signer('secrets!').sign(key))

@app.before_request
def test_before_request():
    #auth = request.authorization
    #if auth:
    #   session['key'] = auth.username

    cookie = request.cookies.get('osf')
    print 'cookie', cookie
    if cookie:
        try:
            g.session_id = itsdangerous.Signer('secrets!').unsign(cookie)
        except itsdangerous.BadSignature:
            pass # create cookie
        print 'cookies', cookie

    print session


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