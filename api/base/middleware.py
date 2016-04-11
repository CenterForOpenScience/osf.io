import sys
import os
import re
import hotshot
import hotshot.stats
import tempfile
import StringIO
import types
import functools

import corsheaders.middleware
from django.conf import settings
from raven.contrib.django.raven_compat.models import sentry_exception_handler

from framework.mongo.handlers import (
    connection_before_request,
    connection_teardown_request
)
from framework.postcommit_tasks.handlers import (
    postcommit_after_request,
    postcommit_before_request
)
from framework.celery_tasks.handlers import (
    celery_before_request,
    celery_after_request,
    celery_teardown_request
)
from framework.transactions.handlers import (
    transaction_before_request,
    transaction_after_request,
    transaction_teardown_request
)
from .api_globals import api_globals
from api.base import settings as api_settings


class MongoConnectionMiddleware(object):
    """MongoDB Connection middleware."""

    def process_request(self, request):
        connection_before_request()

    def process_response(self, request, response):
        connection_teardown_request()
        return response


class CeleryTaskMiddleware(object):
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


class TokuTransactionMiddleware(object):
    """TokuMX Transaction middleware."""

    def process_request(self, request):
        """Begin a transaction if one doesn't already exist."""
        transaction_before_request()

    def process_exception(self, request, exception):
        """If an exception occurs, rollback the current transaction
        if it exists.
        """
        sentry_exception_handler(request=request)
        transaction_teardown_request(error=True)
        return None

    def process_response(self, request, response):
        """Commit transaction if it exists, rolling back in an
        exception occurs.
        """
        transaction_after_request(response, base_status_code_error=400)
        return response


class DjangoGlobalMiddleware(object):
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
        return response


class CorsMiddleware(corsheaders.middleware.CorsMiddleware):
    """
    Augment CORS origin white list with the Institution model's domains.
    """
    def process_request(self, request):
        def origin_not_found_in_white_lists(self, request, origin, url):
            not_found = super(CorsMiddleware, self).origin_not_found_in_white_lists(origin, url)
            if not_found:
                # Check if origin is in the dynamic Institutions whitelist
                if url.netloc.lower() in api_settings.INSTITUTION_ORIGINS_WHITELIST:
                    return False
                # Check if a cross-origin request using the Authorization header
                elif not request.COOKIES:
                    if request.META.get('HTTP_AUTHORIZATION'):
                        return False
                    elif (
                        request.method == 'OPTIONS' and
                        'HTTP_ACCESS_CONTROL_REQUEST_METHOD' in request.META and
                        'authorization' in request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS', '').split(', ')
                    ):
                        return False
            return not_found
        # Re-bind origin_not_found_in_white_lists to the instance with
        # the request as the first arguments
        self.origin_not_found_in_white_lists = functools.partial(
            types.MethodType(origin_not_found_in_white_lists, self),
            request
        )
        return super(CorsMiddleware, self).process_request(request)


class PostcommitTaskMiddleware(object):
    """
    Handle postcommit tasks for django.
    """
    def process_request(self, request):
        postcommit_before_request()

    def process_response(self, request, response):
        postcommit_after_request(response=response, base_status_error_code=400)
        return response


# Orignal version taken from http://www.djangosnippets.org/snippets/186/
# Original author: udfalkso
# Modified by: Shwagroo Team and Gun.io
class ProfileMiddleware(object):
    """
    Displays hotshot profiling for any view.
    http://yoursite.com/yourview/?prof
    Add the "prof" key to query string by appending ?prof (or &prof=)
    and you'll see the profiling results in your browser.
    It's set up to only be available in django's debug mode, is available for superuser otherwise,
    but you really shouldn't add this middleware to any production configuration.
    WARNING: It uses hotshot profiler which is not thread safe.
    """
    def process_request(self, request):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.tmpfile = tempfile.mktemp()
            self.prof = hotshot.Profile(self.tmpfile)

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            return self.prof.runcall(callback, request, *callback_args, **callback_kwargs)

    def get_group(self, file):
        for g in [re.compile('^.*/django/[^/]+'), re.compile('^(.*)/[^/]+$'), re.compile('.*')]:
            name = g.findall(file)
            if name:
                return name[0]

    def get_summary(self, results_dict, sum):
        list = [(item[1], item[0]) for item in results_dict.items()]
        list.sort(reverse=True)
        list = list[:40]

        res = "      tottime\n"
        for item in list:
            res += "%4.1f%% %7.3f %s\n" % (100 * item[0] / sum if sum else 0, item[0], item[1])

        return res

    def summary_for_files(self, stats_str):
        stats_str = stats_str.split("\n")[5:]

        mystats = {}
        mygroups = {}

        sum = 0

        for s in stats_str:
            fields = re.compile(r'\s+').split(s)
            if len(fields) == 7:
                time = float(fields[2])
                sum += time
                file = fields[6].split(":")[0]

                if file not in mystats:
                    mystats[file] = 0
                mystats[file] += time

                group = self.get_group(file)
                if group not in mygroups:
                    mygroups[group] = 0
                mygroups[group] += time

        return "<pre>" + \
               " ---- By file ----\n\n" + self.get_summary(mystats, sum) + "\n" + \
               " ---- By group ---\n\n" + self.get_summary(mygroups, sum) + \
               "</pre>"

    def process_response(self, request, response):
        if (settings.DEBUG or request.user.is_superuser) and 'prof' in request.GET:
            self.prof.close()

            out = StringIO.StringIO()
            old_stdout = sys.stdout
            sys.stdout = out

            stats = hotshot.stats.load(self.tmpfile)
            stats.sort_stats('time', 'calls')
            stats.print_stats()

            sys.stdout = old_stdout
            stats_str = out.getvalue()

            if response and response.content and stats_str:
                response.content = "<pre>" + stats_str + "</pre>"

            response.content = "\n".join(response.content.split("\n")[:40])

            response.content += self.summary_for_files(stats_str)

            os.unlink(self.tmpfile)

        return response
