from framework.flask import app, abort

from framework.exceptions import HTTPError
import httplib as http

import bson.objectid
import itsdangerous
from flask import request, redirect
from werkzeug.local import LocalProxy

COOKIE_NAME = 'osf'
SECRET_KEY = '4IdgL9FYyZRoDkoQ'

# todo 2-back page view queue
# todo actively_editing date

from model import Session

def set_previous_url(url=None):
    if url is None:
        url = request.referrer
    session.data['url_previous'] = url


def goback():
    url_previous = session.data.get('url_previous')
    if url_previous:
        del session.data['url_previous']
        return redirect(url_previous)


def create_session(response, data=None):
    session_id = str(bson.objectid.ObjectId())
    cookie_value = itsdangerous.Signer(SECRET_KEY).sign(session_id)
    response.set_cookie(COOKIE_NAME, value=cookie_value)
    session = Session(_id=session_id, data=data or {})
    session.save()
    sessions[request._get_current_object()] = session
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
        api_label = request.authorization.username
        api_key = ApiKey.load(request.authorization.password)

        session = SessionDict(COLLECTION, TEMP_SESSION)

        if api_key:
            user = api_key.user__keyed and api_key.user__keyed[0]
            node = api_key.node__keyed and api_key.node__keyed[0]
            session = Session()
            session.data['auth_api_label'] = api_label
            session.data['auth_api_key'] = api_key._primary_key
            if user:
                session.data['auth_user_username'] = user.username
                session.data['auth_user_id'] = user._primary_key
                session.data['auth_user_fullname'] = user.fullname

            elif node:
                session.data['auth_node_id'] = node._primary_key

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
            session = Session.load(session_id) or Session(_id=session_id)
            sessions[request._get_current_object()] = session
            return
        except:
            pass
    # TODO: Create session in before_request, cookie in after_request
    # Retry request, preserving status code
    response = redirect(request.path, code=307)
    return create_session(response)

@app.after_request
def after_request(response):
    # Save if session exists and not authenticated by API
    if session._get_current_object() is not None \
<<<<<<< HEAD
            and session.key != TEMP_SESSION:
        session._flush()
    return response
=======
            and not session.data.get('auth_api_key'):
        session.save()
    return response
>>>>>>> e08bd6bd92ff5ead9fc1797be4288a16dbf99824
