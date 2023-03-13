from importlib import import_module

from rest_framework import status as http_status
from future.moves.urllib.parse import urlparse, parse_qs, urlunparse, urlencode

from django.apps import apps
from django.utils import timezone
from django.conf import settings as django_conf_settings
import itsdangerous
from flask import request
import furl
from werkzeug.local import LocalProxy

from framework.celery_tasks.handlers import enqueue_task
from framework.flask import redirect
from osf.utils.fields import ensure_str
from osf.exceptions import InvalidCookieOrSessionError
from website import settings
from website.util import web_url_for

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


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


def get_session_from_cookie(cookie):
    """Return a Django ``SessionStore`` object if cookie is valid and session_key exists.
    Raise ``InvalidCookieOrSessionError`` otherwise.
    """
    try:
        session_key = ensure_str(itsdangerous.Signer(settings.SECRET_KEY).unsign(cookie))
        if not SessionStore().exists(session_key=session_key):
            raise InvalidCookieOrSessionError
        return SessionStore(session_key=session_key)
    except itsdangerous.BadSignature:
        raise InvalidCookieOrSessionError


# TODO: rename to `get_existing_or_create_blank_session()`
def get_session(ignore_cookie=False):
    """
    Get the existing session from the request context or create a new blank Django ``SessionStore`` object.
    Case 0: If cookie does not exist, simply return a new ``SessionStore`` object. This SessionStore object is
            empty, it is not saved to the Session backend (DB or Cache), and it doesn't have a ``session_key``.
            It is the caller of ``get_session()`` that takes care of the ``.save()`` when needed.
    Case 1: If ``ignore_cookie`` is ``True``, no matter whether a cookie exists, returns a new blank Django
            ``SessionStore`` object. This is used when V1/Flask request use Basic Authentication.
    Case 2: If cookie exists and if ``ignore_cookie`` is ``False``, return ``get_session_from_cookie(cookie)``
    Case 3: Return None if ``InvalidCookieOrSessionError`` is raised during case 2.
    """
    cookie = request.cookies.get(settings.COOKIE_NAME)
    try:
        return get_session_from_cookie(cookie) if (not ignore_cookie and cookie) else SessionStore()
    except InvalidCookieOrSessionError:
        return None


# TODO: rename to `create_or_update_session_with_set_cookie()`
def create_session(response, data=None):
    """
    Create or update an existing session with information provided in the given `data` dictionary; and return the
    updated session and the set-cookie response as a tuple.
    """
    user_session = get_session()
    if not user_session:
        response.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)
        return None, response
    # TODO: check if session data changed and decide whether to save the session object
    for key, value in data.items() if data else {}:
        user_session[key] = value
    user_session.save()
    cookie_value = itsdangerous.Signer(settings.SECRET_KEY).sign(user_session.session_key)
    if response is not None:
        response.set_cookie(
            settings.COOKIE_NAME,
            value=cookie_value,
            domain=settings.OSF_COOKIE_DOMAIN,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=settings.SESSION_COOKIE_HTTPONLY,
            samesite=settings.SESSION_COOKIE_SAMESITE
        )
        return user_session, response
    return user_session, None


# Note: Use `LocalProxy` to ensure Thread-safe for `werkzeug`.
session = LocalProxy(get_session)


# Request callbacks
# NOTE: This gets attached in website.app.init_app to ensure correct callback order
def before_request():

    # TODO: Fix circular import
    from framework.auth.core import get_user
    from framework.auth import cas
    UserSessionMap = apps.get_model('osf.UserSessionMap')

    # Request Type 1: Service ticket validation during CAS login.
    ticket = request.args.get('ticket')
    if ticket:
        service_url = furl.furl(request.url)
        service_url.args.pop('ticket')
        # Attempt to authenticate wih CAS, and return a proper redirect response
        return cas.make_response_from_ticket(ticket=ticket, service_url=service_url.url)

    # Request Type 2: Basic Auth with username and password in Authorization headers
    # Note: As for flask/V1 request, many views rely on an ``auth`` object that comes from the ``session``
    #       to identify the user. Thus, we still need to keep the session creation and usage here.
    if request.authorization:
        user = get_user(
            email=request.authorization.username,
            password=request.authorization.password
        )
        # Create an empty session
        user_session = get_session(ignore_cookie=True)
        # Although the if check is not necessary based on current ``get_session()`` implementation. However, we
        # keep it here in case ``get_session()`` was changed. It may be removed after we have unit tests for this.
        if not user_session:
            return

        if not user:
            user_session['auth_error_code'] = http_status.HTTP_401_UNAUTHORIZED
            user_session.save()
            return

        user_addon = user.get_addon('twofactor')
        if user_addon and user_addon.is_confirmed:
            otp = request.headers.get('X-OSF-OTP')
            if otp is None or not user_addon.verify_code(otp):
                user_session['auth_error_code'] = http_status.HTTP_401_UNAUTHORIZED
                return
        user_session['auth_user_username'] = user.username
        user_session['auth_user_fullname'] = user.fullname
        if user_session.get('auth_user_id', None) != user._primary_key:
            user_session['auth_user_id'] = user._primary_key
        user_session.save()
        UserSessionMap.objects.create(
            user=user,
            session_key=user_session.session_key,
            expire_date=user_session.get_expiry_date()
        )
        return

    # Request Type 3: Cookie Auth
    cookie = request.cookies.get(settings.COOKIE_NAME)
    if cookie:
        try:
            user_session = get_session_from_cookie(cookie)
        except InvalidCookieOrSessionError:
            response = redirect(web_url_for('index'))
            response.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)
            return response
        # Update date last login when making non-api requests
        from framework.auth.tasks import update_user_from_activity
        try:
            user_session_entry = UserSessionMap.objects.get(session_key=user_session.session_key)
            enqueue_task(
                update_user_from_activity.s(
                    user_session_entry.user._id,
                    timezone.now().timestamp(),
                    cas_login=False
                )
            )
        except UserSessionMap.MultipleObjectsReturned or UserSessionMap.DoesNotExist:
            # TODO: log an error message to sentry
            return None


def after_request(response):
    # Disallow embedding in frames
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response
