from framework.flask import app, abort
from framework.mongo import db

from framework.exceptions import HTTPError
import httplib as http

import bson.objectid
import itsdangerous
from flask import request, redirect
from werkzeug.local import LocalProxy

import datetime

COOKIE_NAME = 'osf'
SECRET_KEY = '4IdgL9FYyZRoDkoQ'
COLLECTION = db['sessions']
TEMP_SESSION = 'tmp'

# todo 2-back page view queue
# todo actively_editing date

class SessionDict(object):

    def __init__(self, db, key):
        self._collection = db
        self.key = key
        self._is_dirty = False

        result = self._collection.find(
            {'_id': self.key},
            {'value': 1, '_id': 0})

        if result.count() == 0:
            self.values = {}
            self.values['session_date_created'] = datetime.datetime.utcnow()
        else:
            self.values = result[0]['value']

    def __setitem__(self, key, value):
        self.values[key] = value
        self._is_dirty = True

    def _flush(self):
        if self._is_dirty:
            self.values['session_date_modified'] = datetime.datetime.utcnow()
            self._collection.update(
                {'_id':self.key},
                {'_id':self.key, 'value':self.values},
                upsert=True
            )
            self._is_dirty = False

    def __delitem__(self, key):
        del self.values[key]
        self._is_dirty = True

    def __getitem__(self, key):
        return self.values[key]

    def __contains__(self, item):
        return item in self.values

    def get(self, item, default=None):
        return self.values.get(item, default)

def set_previous_url(url=None):
    if url is None:
        url = request.referrer
    session['url_previous'] = url


def goback():
    url_previous = session.get('url_previous')
    if url_previous:
        del session['url_previous']
        return redirect(url_previous)


def create_session(response, data=None):
    session_id = str(bson.objectid.ObjectId())
    cookie_value = itsdangerous.Signer(SECRET_KEY).sign(session_id)
    response.set_cookie(COOKIE_NAME, value=cookie_value)
    d = SessionDict(COLLECTION, session_id)
    if data:
        for k,v in data.items():
            d[k] = v
    d._flush()
    sessions[request._get_current_object()] = d
    return response


def get_session():
    try:
        return sessions[request._get_current_object()]
    except:
        return None


from weakref import WeakKeyDictionary
sessions = WeakKeyDictionary()
session = LocalProxy(get_session)

# Request callbacks

@app.before_request
def before_request():

    if request.authorization:

        # Hack: Avoid circular import
        from website.project.model import ApiKey
        api_key = ApiKey.load(request.authorization.username)

        session = SessionDict(COLLECTION, TEMP_SESSION)

        if api_key:

            user = api_key.user__keyed and api_key.user__keyed[0]
            node = api_key.node__keyed and api_key.node__keyed[0]

            session['auth_api_key'] = api_key._primary_key

            if user:
                session['auth_user_username'] = user.username
                session['auth_user_id'] = user._primary_key
                session['auth_user_fullname'] = user.fullname

            elif node:
                session['auth_node_id'] = node._primary_key

            else:
                # Invalid key: Not attached to user or node
                session['auth_error_code'] = http.FORBIDDEN

        else:

            # Invalid key: Not found in database
            session['auth_api_key_valid'] = http.FORBIDDEN

        sessions[request._get_current_object()] = session
        return

    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        try:
            session_id = itsdangerous.Signer(SECRET_KEY).unsign(cookie)
            sessions[request._get_current_object()] = SessionDict(COLLECTION, session_id)
            return
        except:
            pass
    # TODO: Create session in before_request, cookie in after_request
    # Retry request, preserving status code
    response = redirect(request.path, code=307)
    return create_session(response)

@app.after_request
def after_request(response):
    # Flush if session is defined
    if session._get_current_object() is not None \
            and session.key != TEMP_SESSION:
        session._flush()
    return response
