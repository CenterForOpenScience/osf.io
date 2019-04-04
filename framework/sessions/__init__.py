# -*- coding: utf-8 -*-
import datetime as dt
from rest_framework import status as http_status
from future.moves.urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from django.apps import apps
from django.utils import timezone
from django.db.models import Q
import bson.objectid
import itsdangerous
from flask import request
import furl
from weakref import WeakKeyDictionary
from werkzeug.local import LocalProxy

from framework.flask import redirect
from framework.sessions.utils import remove_session
from website import settings


def add_key_to_url(url, scheme, key):
    """Redirects the user to the requests URL with the given key appended to the query parameters."""

    query = request.args.to_dict()
    query['view_only'] = key
    replacements = {'query': urlencode(query)}

    if scheme:
        replacements['scheme'] = scheme

    parsed_url = urlparse(url)

    if parsed_url.fragment:
        # Fragments should exists server side so this mean some one set up a # in the url
        # WSGI sucks and auto unescapes it so we just shove it back into the path with the escaped hash
        replacements['path'] = '{}%23{}'.format(parsed_url.path, parsed_url.fragment)
        replacements['fragment'] = ''

    parsed_redirect_url = parsed_url._replace(**replacements)
    return urlunparse(parsed_redirect_url)


def prepare_private_key():
    """
    `before_request` handler that checks the Referer header to see if the user
    is requesting from a view-only link. If so, re-append the view-only key.

    NOTE: In order to ensure the execution order of the before_request callbacks,
    this is attached in website.app.init_app rather than using @app.before_request.
    """

    # Done if not GET request
    if request.method != 'GET':
        return

    # Done if private_key in args
    if request.args.get('view_only', ''):
        return

    # Grab query key from previous request for not logged-in users
    if request.referrer:
        referrer_parsed = urlparse(request.referrer)
        scheme = referrer_parsed.scheme
        key = parse_qs(urlparse(request.referrer).query).get('view_only')
        if key:
            key = key[0]
    else:
        scheme = None
        key = None

    # Update URL and redirect
    if key and not session.is_authenticated:
        new_url = add_key_to_url(request.url, scheme, key)
        return redirect(new_url, code=http_status.HTTP_307_TEMPORARY_REDIRECT)


def get_session():
    Session = apps.get_model('osf.Session')
    user_session = sessions.get(request._get_current_object())
    if not user_session:
        user_session = Session()
        set_session(user_session)
    return user_session


def set_session(session):
    sessions[request._get_current_object()] = session


def create_session(response, data=None):
    Session = apps.get_model('osf.Session')
    current_session = get_session()
    if current_session:
        current_session.data.update(data or {})
        current_session.save()
        cookie_value = itsdangerous.Signer(settings.SECRET_KEY).sign(current_session._id)
    else:
        session_id = str(bson.objectid.ObjectId())
        new_session = Session(_id=session_id, data=data or {})
        new_session.save()
        cookie_value = itsdangerous.Signer(settings.SECRET_KEY).sign(session_id)
        set_session(new_session)
    if response is not None:
        response.set_cookie(settings.COOKIE_NAME, value=cookie_value, domain=settings.OSF_COOKIE_DOMAIN,
                            secure=settings.SESSION_COOKIE_SECURE, httponly=settings.SESSION_COOKIE_HTTPONLY)
        return response


sessions = WeakKeyDictionary()
session = LocalProxy(get_session)


# Request callbacks
# NOTE: This gets attached in website.app.init_app to ensure correct callback order
def before_request():
    # TODO: Fix circular import
    from framework.auth.core import get_user
    from framework.auth import cas
    from framework.utils import throttle_period_expired
    Session = apps.get_model('osf.Session')

    # Central Authentication Server Ticket Validation and Authentication
    ticket = request.args.get('ticket')
    if ticket:
        service_url = furl.furl(request.url)
        service_url.args.pop('ticket')
        # Attempt to authenticate wih CAS, and return a proper redirect response
        return cas.make_response_from_ticket(ticket=ticket, service_url=service_url.url)

    if request.authorization:
        user = get_user(
            email=request.authorization.username,
            password=request.authorization.password
        )
        # Create an empty session
        # TODO: Shoudn't need to create a session for Basic Auth
        user_session = Session()
        set_session(user_session)

        if user:
            user_addon = user.get_addon('twofactor')
            if user_addon and user_addon.is_confirmed:
                otp = request.headers.get('X-OSF-OTP')
                if otp is None or not user_addon.verify_code(otp):
                    # Must specify two-factor authentication OTP code or invalid two-factor authentication OTP code.
                    user_session.data['auth_error_code'] = http_status.HTTP_401_UNAUTHORIZED
                    return
            user_session.data['auth_user_username'] = user.username
            user_session.data['auth_user_fullname'] = user.fullname
            if user_session.data.get('auth_user_id', None) != user._primary_key:
                user_session.data['auth_user_id'] = user._primary_key
                user_session.save()
        else:
            # Invalid key: Not found in database
            user_session.data['auth_error_code'] = http_status.HTTP_401_UNAUTHORIZED
        return

    cookie = request.cookies.get(settings.COOKIE_NAME)
    if cookie:
        try:
            session_id = itsdangerous.Signer(settings.SECRET_KEY).unsign(cookie)
            user_session = Session.load(session_id) or Session(_id=session_id)
        except itsdangerous.BadData:
            return
        if not throttle_period_expired(user_session.created, settings.OSF_SESSION_TIMEOUT):
            # Update date last login when making non-api requests
            if user_session.data.get('auth_user_id') and 'api' not in request.url:
                OSFUser = apps.get_model('osf.OSFUser')
                (
                    OSFUser.objects
                    .filter(guids___id__isnull=False, guids___id=user_session.data['auth_user_id'])
                    # Throttle updates
                    .filter(Q(date_last_login__isnull=True) | Q(date_last_login__lt=timezone.now() - dt.timedelta(seconds=settings.DATE_LAST_LOGIN_THROTTLE)))
                ).update(date_last_login=timezone.now())
            set_session(user_session)
        else:
            remove_session(user_session)


def after_request(response):
    # Disallow embedding in frames
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response
