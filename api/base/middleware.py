import gc
from io import StringIO
import cProfile
import pstats
import threading

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from raven.contrib.django.raven_compat.models import sentry_exception_handler
import corsheaders.middleware

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


class CeleryTaskMiddleware(MiddlewareMixin):
    """Celery Task middleware."""

    def process_request(self, request):
        celery_before_request()

    def process_exception(self, request, exception):
        """If an exception occurs, clear the celery task queue so process_response has nothing."""
        sentry_exception_handler(request=request)
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
        sentry_exception_handler(request=request)
        api_globals.request = None
        return None

    def process_response(self, request, response):
        api_globals.request = None
        if api_settings.DEBUG and len(gc.get_referents(request)) > 2:
            raise Exception('You wrote a memory leak. Stop it')
        return response


class CorsMiddleware(corsheaders.middleware.CorsMiddleware):
    """
    Augment CORS origin white list with the Institution model's domains.
    """

    _context = threading.local()

    def origin_found_in_white_lists(self, origin, url):
        settings.CORS_ORIGIN_WHITELIST += api_settings.ORIGINS_WHITELIST
        # Check if origin is in the dynamic custom domain whitelist
        found = super(CorsMiddleware, self).origin_found_in_white_lists(origin, url)
        # Check if a cross-origin request using the Authorization header
        if not found:
            if not self._context.request.COOKIES:
                if self._context.request.META.get('HTTP_AUTHORIZATION'):
                    return True
                elif (
                    self._context.request.method == 'OPTIONS' and
                    'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in self._context.request.META and
                    'authorization' in list(map(
                        lambda h: h.strip(),
                        self._context.request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '').split(','),
                    ))
                ):
                    return True

        return found

    def process_response(self, request, response):
        self._context.request = request
        try:
            return super(CorsMiddleware, self).process_response(request, response)
        finally:
            self._context.request = None


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
