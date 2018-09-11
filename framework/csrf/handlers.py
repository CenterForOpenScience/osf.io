# -*- coding: utf-8 -*-
from django.conf import settings as api_settings
from django.middleware.csrf import _get_new_csrf_token, _sanitize_token
from framework.auth.core import get_current_user_id
from flask import request, g

# Mostly a port of django.middleware.csrf.CsrfMiddleware._get_token
# with the session bits removed
def _get_token():
    try:
        cookie_token = request.cookies[api_settings.CSRF_COOKIE_NAME]
    except KeyError:
        return None

    csrf_token = _sanitize_token(cookie_token)
    if csrf_token != cookie_token:
        # Cookie token needed to be replaced;
        # the cookie needs to be reset.
        g.csrf_cookie_needs_reset = True
    return csrf_token


def before_request():
    # Reuse token if already set
    csrf_token = _get_token()
    if not csrf_token or g.get('csrf_cookie_needs_reset', False):
        csrf_token = _get_new_csrf_token()
    # Store csrf_token on g so that it can be used in
    # server-rendered forms
    g.csrf_token = csrf_token


def after_request(resp):
    """Set a cookie specified by api_settings.CSRF_COOKI_NAME so that
    session-authenticated requests from the legacy frontend can pass
    CSRF verification.
    """
    if get_current_user_id():
        csrf_token = g.csrf_token
        # Set the CSRF cookie even if it's already set, so we renew
        # the expiry timer.
        resp.set_cookie(
            api_settings.CSRF_COOKIE_NAME,
            csrf_token,
            max_age=api_settings.CSRF_COOKIE_AGE,
            domain=api_settings.CSRF_COOKIE_DOMAIN,
            path=api_settings.CSRF_COOKIE_PATH,
            httponly=api_settings.CSRF_COOKIE_HTTPONLY,
        )

    return resp


handlers = {
    'before_request': before_request,
    'after_request': after_request,
}
