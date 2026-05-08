import gc
from io import StringIO
import cProfile
import pstats
from importlib import import_module

from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.deprecation import MiddlewareMixin
from sentry_sdk import init
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from framework.postcommit_tasks.handlers import (
    postcommit_after_request,
    postcommit_before_request,
)
from framework.celery_tasks.handlers import (
    celery_before_request,
    celery_after_request,
    celery_teardown_request,
)
from .api_globals import api_globals
from api.base import settings as api_settings
from api.base.authentication.drf import drf_get_session_from_cookie

SessionStore = import_module(settings.SESSION_ENGINE).SessionStore


enabled = (not settings.DEV_MODE) and settings.SENTRY_DSN
if enabled:
    init(
        dsn=settings.SENTRY_DSN,
        integrations=[CeleryIntegration(), DjangoIntegration(), FlaskIntegration()],
    )

class CeleryTaskMiddleware(MiddlewareMixin):
    """Celery Task middleware."""

    def process_request(self, request):
        celery_before_request()

    def process_exception(self, request, exception):
        """If an exception occurs, clear the celery task queue so process_response has nothing."""
        celery_teardown_request(error=True)
        return None

    def process_response(self, request, response):
        """Clear the celery task queue if the response status code is 400 or above"""
        celery_after_request(response, base_status_code_error=400)
        celery_teardown_request()
        return response


class DjangoGlobalMiddleware(MiddlewareMixin):
    """
    Store request object on a thread-local variable for use in database caching mechanism.
    """

    def process_request(self, request):
        api_globals.request = request

    def process_exception(self, request, exception):
        api_globals.request = None
        return None

    def process_response(self, request, response):
        api_globals.request = None
        if api_settings.DEBUG and len(gc.get_referents(request)) > 2:
            raise Exception('You wrote a memory leak. Stop it')
        return response


class PostcommitTaskMiddleware(MiddlewareMixin):
    """
    Handle postcommit tasks for django.
    """

    def process_request(self, request):
        postcommit_before_request()

    def process_response(self, request, response):
        postcommit_after_request(response=response, base_status_error_code=400)
        return response


# Adapted from http://www.djangosnippets.org/snippets/186/
# Original author: udfalkso
# Modified by: Shwagroo Team and Gun.io
# Modified by: COS
class ProfileMiddleware(MiddlewareMixin):
    """
    Displays hotshot profiling for any view.
    http://yoursite.com/yourview/?prof
    Add the "prof" key to query string by appending ?prof (or &prof=)
    and you'll see the profiling results in your browser.
    It's set up to only be available in django's debug mode, is available for superuser otherwise,
    but you really shouldn't add this middleware to any production configuration.
    """

    def process_request(self, request):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof = cProfile.Profile()

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof.enable()

    def process_response(self, request, response):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof.disable()

            s = StringIO.StringIO()
            ps = pstats.Stats(self.prof, stream=s).sort_stats('cumtime')
            ps.print_stats()
            response.content = s.getvalue()

        return response


# import time
# from importlib import import_module

# from django.contrib.sessions.backends.base import UpdateError
# from django.contrib.sessions.exceptions import SessionInterrupted
# from django.utils.cache import patch_vary_headers
# from django.utils.deprecation import MiddlewareMixin
# from django.utils.http import http_date


class UnsignCookieSessionMiddleware(SessionMiddleware):
    """
    Overrides the process_request hook of SessionMiddleware
    to retrieve the session key for finding the correct session
    by unsigning the cookie value using server secret
    """

    def process_request(self, request):
        cookie = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        if cookie:
            request.session = drf_get_session_from_cookie(cookie)
        else:
            request.session = SessionStore()

    # Example of process_response with session cookie signing. Not used currently as signing is done in auth_login view and session cookie is set there.
    # def process_response(self, request, response):
    #     """
    #     If request.session was modified, or if the configuration is to save the
    #     session every time, save the changes and set a session cookie or delete
    #     the session cookie if the session has been emptied.
    #     """
    #     try:
    #         accessed = request.session.accessed
    #         modified = request.session.modified
    #         empty = request.session.is_empty()
    #     except AttributeError:
    #         return response
    #     # First check if we need to delete this cookie.
    #     # The session should be deleted only if the session is entirely empty.
    #     if settings.SESSION_COOKIE_NAME in request.COOKIES and empty:
    #         response.delete_cookie(
    #             settings.SESSION_COOKIE_NAME,
    #             path=settings.SESSION_COOKIE_PATH,
    #             domain=settings.SESSION_COOKIE_DOMAIN,
    #             samesite=settings.SESSION_COOKIE_SAMESITE,
    #         )
    #         patch_vary_headers(response, ("Cookie",))
    #     else:
    #         if accessed:
    #             patch_vary_headers(response, ("Cookie",))
    #         if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
    #             if request.session.get_expire_at_browser_close():
    #                 max_age = None
    #                 expires = None
    #             else:
    #                 max_age = request.session.get_expiry_age()
    #                 expires_time = time.time() + max_age
    #                 expires = http_date(expires_time)
    #             # Save the session data and refresh the client cookie.
    #             # Skip session save for 5xx responses.
    #             if response.status_code < 500:
    #                 try:
    #                     request.session.save()
    #                 except UpdateError:
    #                     raise SessionInterrupted(
    #                         "The request's session was deleted before the "
    #                         "request completed. The user may have logged "
    #                         "out in a concurrent request, for example."
    #                     )

    #                 from osf.utils.fields import ensure_str
    #                 import itsdangerous

    #                 signed_session_key = ensure_str(itsdangerous.Signer(settings.SECRET_KEY).sign(request.session.session_key))
    #                 response.set_cookie(
    #                     settings.SESSION_COOKIE_NAME,
    #                     signed_session_key,
    #                     max_age=max_age,
    #                     expires=expires,
    #                     domain=settings.SESSION_COOKIE_DOMAIN,
    #                     path=settings.SESSION_COOKIE_PATH,
    #                     secure=settings.SESSION_COOKIE_SECURE or None,
    #                     httponly=settings.SESSION_COOKIE_HTTPONLY or None,
    #                     samesite=settings.SESSION_COOKIE_SAMESITE,
    #                 )
    #     return response
