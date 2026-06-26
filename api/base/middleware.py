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
