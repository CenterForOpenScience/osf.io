from framework.transactions import handlers, commands
from pymongo.errors import OperationFailure

class TokuTransactionsMiddleware(object):
    """TokuMX transaction middleware."""

    def process_request(self, request):
        handlers.transaction_before_request()

    def process_exception(self, request, exception):
        commands.rollback()

    def process_response(self, request, response):
        try:
            return handlers.transaction_after_request(response)
        except OperationFailure:
            return response
