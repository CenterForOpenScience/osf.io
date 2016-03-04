from modularodm import Q
from pymongo.errors import OperationFailure
from raven.contrib.django.raven_compat.models import sentry_exception_handler

import corsheaders.middleware

from framework.tasks.handlers import (
    celery_before_request,
    celery_teardown_request
)
from framework.transactions import commands, messages, utils
from website.institutions.model import Institution

from .api_globals import api_globals

from api.base import settings


# TODO: Verify that a transaction is being created for every
# individual request.
class TokuTransactionsMiddleware(object):
    """TokuMX transaction middleware."""

    def process_request(self, request):
        """Begin a transaction if one doesn't already exist."""
        try:
            commands.begin()
        except OperationFailure as err:
            message = utils.get_error_message(err)
            if messages.TRANSACTION_EXISTS_ERROR not in message:
                raise err

    def process_exception(self, request, exception):
        """If an exception occurs, rollback the current transaction
        if it exists.
        """
        sentry_exception_handler(request=request)
        try:
            commands.rollback()
        except OperationFailure as err:
            message = utils.get_error_message(err)
            if messages.NO_TRANSACTION_ERROR not in message:
                raise
        commands.disconnect()
        return None

    def process_response(self, request, response):
        """Commit transaction if it exists, rolling back in an
        exception occurs.
        """

        try:
            if response.status_code >= 400:
                commands.rollback()
            else:
                commands.commit()
        except OperationFailure as err:
            message = utils.get_error_message(err)
            if messages.NO_TRANSACTION_TO_COMMIT_ERROR not in message:
                if settings.DEBUG_TRANSACTIONS:
                    pass
                else:
                    raise err
        except Exception as err:
            try:
                commands.rollback()
            except OperationFailure:
                pass
            else:
                raise err
        commands.disconnect()
        return response


class DjangoGlobalMiddleware(object):
    """
    Store request object on a thread-local variable for use in database caching mechanism.
    """
    def process_request(self, request):
        api_globals.request = request
        celery_before_request()

    def process_exception(self, request, exception):
        sentry_exception_handler(request=request)
        api_globals.request = None
        return None

    def process_response(self, request, response):
        celery_teardown_request()
        api_globals.request = None
        return response


class CorsMiddleware(corsheaders.middleware.CorsMiddleware):
    """
    Augment CORS origin white list with the Institution model's domains.
    """
    def origin_not_found_in_white_lists(self, origin, url):
        not_found = (url.netloc not in settings.CORS_ORIGIN_WHITELIST and not self.regex_domain_match(origin))
        if not_found:
            not_found = Institution.find(Q('domain', 'eq', url.netloc.lower())).count() == 0
        return not_found
