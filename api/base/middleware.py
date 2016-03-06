from raven.contrib.django.raven_compat.models import sentry_exception_handler

from framework.mongo.handlers import (
    connection_before_request,
    connection_teardown_request
)
from framework.tasks.handlers import (
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
        """Clear the celery task queue if the response status code in the 400 or above range"""
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
