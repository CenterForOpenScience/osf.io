from framework.transactions import commands, messages, utils
from pymongo.errors import OperationFailure

from flask import _app_ctx_stack, Flask

dummy_app = Flask(__name__)

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
            commands.commit()
        except OperationFailure as err:
            message = utils.get_error_message(err)
            if messages.NO_TRANSACTION_TO_COMMIT_ERROR not in message:
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


class FlaskRequestMiddleWare(object):
    """
    Push and pop new flask request contexts alongside Django requests

    This is required to prevent caching issues with ModularODM, since (Flask)StoredObject is keyed on the flask
    request object.
    """
    def process_request(self, request):
        ## Called on every request, so self.flask_ctx should always be defined
        self.flask_ctx = dummy_app.test_request_context()
        self.flask_ctx.push()

    def process_exception(self, request, exception):
        if _app_ctx_stack.top is not None:
            self.flask_ctx.pop()

    def process_response(self, request, response):
        if _app_ctx_stack.top is not None:
            self.flask_ctx.pop()
        return response
