from framework.transactions import handlers, commands

class TokuTransactionsMiddleware(object):
    """TokuMX transaction middleware."""

    def process_request(self, request):
        handlers.transaction_before_request()

    def process_exception(self, request, exception):
        commands.rollback()

    def process_response(self, request, response):
        return handlers.transaction_after_request(response)
