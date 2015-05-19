# -*- coding: utf-8 -*-

import furl
import urllib
import urlparse
import bson.objectid
import httplib as http

import itsdangerous

from werkzeug.local import LocalProxy
from weakref import WeakKeyDictionary
from flask import request, make_response, jsonify
from framework.flask import app, redirect

from website import settings

from .model import Session


def add_key_to_url(url, scheme, key):
    """Redirects the user to the requests URL with the given key appended
    to the query parameters.

    """
    query = request.args.to_dict()
    query['view_only'] = key
    replacements = {'query': urllib.urlencode(query)}

    if scheme:
        replacements['scheme'] = scheme

    parsed_url = urlparse.urlparse(url)

    if parsed_url.fragment:
        # Fragments should exists server side so this mean some one set up a # in the url
        # WSGI sucks and auto unescapes it so we just shove it back into the path with the escaped hash
        replacements['path'] = '{}%23{}'.format(parsed_url.path, parsed_url.fragment)
        replacements['fragment'] = ''

    parsed_redirect_url = parsed_url._replace(**replacements)
    return urlparse.urlunparse(parsed_redirect_url)


def prepare_private_key():
    """`before_request` handler that checks the Referer header to see if the user
    is requesting from a view-only link. If so, reappend the view-only key.

    NOTE: In order to ensure the execution order of the before_request callbacks,
    this is attached in website.app.init_app rather than using
    @app.before_request.
    """

    # Done if not GET request
    if request.method != 'GET':
        return

    # Done if private_key in args
    key_from_args = request.args.get('view_only', '')
    if key_from_args:
        return

    # grab query key from previous request for not login user
    if request.referrer:
        referrer_parsed = urlparse.urlparse(request.referrer)
        scheme = referrer_parsed.scheme
        key = urlparse.parse_qs(
            urlparse.urlparse(request.referrer).query
        ).get('view_only')
        if key:
            key = key[0]
    else:
        scheme = None
        key = None

    # Update URL and redirect
    if key and not session:
        new_url = add_key_to_url(request.url, scheme, key)
        return redirect(new_url, code=http.TEMPORARY_REDIRECT)


# todo 2-back page view queue
# todo actively_editing date

def set_previous_url(url=None):
    """Add current URL to session history if not in excluded list; cap history
    at set length.
    Does nothing if a user is not logged in

    """
    if not session:
        return

    url = url or request.path
    if any([rule(url) for rule in settings.SESSION_HISTORY_IGNORE_RULES]):
        return
    session.data['history'].append(url)
    while len(session.data['history']) > settings.SESSION_HISTORY_LENGTH:
        session.data['history'].pop(0)


def goback(n=1):
    next_url = request.args.get('next') or request.form.get('next_url')
    if next_url:
        return redirect(next_url)
    if session._get_current_object() is None:
        return redirect('/')
    try:
        for _ in range(n):
            url = session.data['history'].pop()
    except IndexError:
        url = '/dashboard/'
    return redirect(url)


def get_session():
    return sessions.get(request._get_current_object())


def set_session(session):
    sessions[request._get_current_object()] = session


def create_session(response, data=None):
    current_session = get_session()
    if current_session:
        current_session.data.update(data or {})
        current_session.save()
        cookie_value = itsdangerous.Signer(settings.SECRET_KEY).sign(current_session._id)
    else:
        session_id = str(bson.objectid.ObjectId())
        session = Session(_id=session_id, data=data or {})
        session.save()
        cookie_value = itsdangerous.Signer(settings.SECRET_KEY).sign(session_id)
        set_session(session)
    if response is not None:
        response.set_cookie(settings.COOKIE_NAME, value=cookie_value)
        return response


sessions = WeakKeyDictionary()
session = LocalProxy(get_session)

# Request callbacks

# NOTE: This gets attached in website.app.init_app to ensure correct callback
# order
def before_request():
    from framework.auth import authenticate
    from framework.auth.core import User
    from framework.auth import cas

    # Central Authentication Server Ticket Validation and Authentication
    ticket = request.args.get('ticket')
    if ticket:
        service_url = furl.furl(request.url)
        service_url.args.pop('ticket')
        # Attempt autn wih CAS, and return a proper redirect response
        return cas.make_response_from_ticket(ticket=ticket, service_url=service_url.url)

    # Central Authentication Server OAuth Bearer Token
    authorization = request.headers.get('Authorization')
    if authorization and authorization.startswith('Bearer '):
        client = cas.get_client()
        try:
            access_token = cas.parse_auth_header(authorization)
        except cas.CasTokenError as err:
            # NOTE: We assume that the request is an AJAX request
            return jsonify({'message_short': 'Invalid Bearer token', 'message_long': err.args[0]}), http.UNAUTHORIZED
        cas_resp = client.profile(access_token)
        if cas_resp.authenticated:
            user = User.load(cas_resp.user)
            return authenticate(user, access_token=access_token, response=None)
        return make_response('', http.UNAUTHORIZED)

    if request.authorization:
        # Create a session from the API key; if key is
        # not valid, save the HTTP error code in the
        # "auth_error_code" field of session.data

        # Create empty session
        session = Session()

        # Hack: Avoid circular import
        from website.project.model import ApiKey

        api_label = request.authorization.username
        api_key_id = request.authorization.password
        api_key = ApiKey.load(api_key_id)

        if api_key:
            user = api_key.user__keyed and api_key.user__keyed[0]
            node = api_key.node__keyed and api_key.node__keyed[0]

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
                session.data['auth_error_code'] = http.FORBIDDEN
        else:
            # Invalid key: Not found in database
            session.data['auth_error_code'] = http.FORBIDDEN

        set_session(session)
        return

    cookie = request.cookies.get(settings.COOKIE_NAME)
    if cookie:
        try:
            session_id = itsdangerous.Signer(settings.SECRET_KEY).unsign(cookie)
            session = Session.load(session_id) or Session(_id=session_id)
            set_session(session)
            return
        except:
            pass
    ## TODO: Create session in before_request, cookie in after_request
    ## Retry request, preserving status code
    #response = redirect(request.path, code=307)
    return create_session(None)


@app.after_request
def after_request(response):
    # Save if session exists and not authenticated by API
    set_previous_url()
    if session._get_current_object() is not None \
            and not session.data.get('auth_api_key'):
        session.save()
    return response
