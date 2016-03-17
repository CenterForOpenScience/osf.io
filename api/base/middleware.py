from modularodm import Q
from raven.contrib.django.raven_compat.models import sentry_exception_handler

import corsheaders.middleware

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
from website.models import Institution
from framework.transactions.handlers import (
    transaction_before_request,
    transaction_after_request,
    transaction_teardown_request
)
from .api_globals import api_globals


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
    def origin_not_found_in_white_lists(self, origin, url):
        not_found = super(CorsMiddleware, self).origin_not_found_in_white_lists(origin, url)
        if not_found:
            not_found = Institution.find(Q('domains', 'eq', url.netloc.lower())).count() == 0
        return not_found


class PostcommitTaskMiddleware(object):
    """
    Handle postcommit tasks for django.
    """
    def process_request(self, request):
        postcommit_before_request()

    def process_response(self, request, response):
        postcommit_after_request(response=response, base_status_error_code=400)
        return response
