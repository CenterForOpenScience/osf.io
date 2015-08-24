# -*- coding: utf-8 -*-

import bson.objectid
import furl
import httplib as http
import urllib
import urlparse

import itsdangerous

from werkzeug.local import LocalProxy
from weakref import WeakKeyDictionary
from flask import request, make_response
from framework.exceptions import HTTPError
from framework.flask import redirect

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
    if key and not session.is_authenticated:
        new_url = add_key_to_url(request.url, scheme, key)
        return redirect(new_url, code=http.TEMPORARY_REDIRECT)


def get_session():
    session = sessions.get(request._get_current_object())
    if not session:
        session = Session()
        set_session(session)
    return session


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
        response.set_cookie(settings.COOKIE_NAME, value=cookie_value, domain=settings.OSF_COOKIE_DOMAIN)
        return response


sessions = WeakKeyDictionary()
session = LocalProxy(get_session)

# Request callbacks

# NOTE: This gets attached in website.app.init_app to ensure correct callback
# order
def before_request():
    from framework import sentry
    from framework.auth import cas
    from framework.auth.core import User
    from framework.auth import authenticate
    from framework.routing import json_renderer

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
        # Non-API routes should only respond to bearer tokens if the request comes from a whitelisted service
        if request.remote_addr not in settings.WATERBUTLER_ADDRS:
            raise HTTPError(http.FORBIDDEN)

        client = cas.get_client()
        try:
            access_token = cas.parse_auth_header(authorization)
            cas_resp = client.profile(access_token)
        except cas.CasError as err:
            sentry.log_exception()
            # NOTE: We assume that the request is an AJAX request
            return json_renderer(err)
        if cas_resp.authenticated:
            user = User.load(cas_resp.user)
            return authenticate(user, access_token=access_token, response=None)
        return make_response('', http.UNAUTHORIZED)

    if request.authorization:
        # TODO: Fix circular import
        from framework.auth.core import get_user
        user = get_user(
            email=request.authorization.username,
            password=request.authorization.password
        )
        # Create empty session
        # TODO: Shoudn't need to create a session for Basic Auth
        session = Session()

        if user:
            session.data['auth_user_username'] = user.username
            session.data['auth_user_id'] = user._primary_key
            session.data['auth_user_fullname'] = user.fullname
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


def after_request(response):
    if session.data.get('auth_user_id'):
        session.save()

    return response
