# -*- coding: utf-8 -*-

import httplib
import logging

from flask import request, current_app
from pymongo.errors import OperationFailure

from framework.transactions import utils, commands, messages

from website import settings


LOCK_ERROR_CODE = httplib.BAD_REQUEST
NO_AUTO_TRANSACTION_ATTR = '_no_auto_transaction'

logger = logging.getLogger(__name__)


def no_auto_transaction(func):
    setattr(func, NO_AUTO_TRANSACTION_ATTR, True)
    return func


def view_has_annotation(attr):
    try:
        endpoint = request.url_rule.endpoint
    except (RuntimeError, AttributeError):
        return False
    view = current_app.view_functions[endpoint]
    return getattr(view, attr, False)


def transaction_before_request():
    """Setup transaction before handling the request.
    """
    if view_has_annotation(NO_AUTO_TRANSACTION_ATTR):
        return None
    try:
        commands.rollback()
        logger.error('Transaction already in progress; rolling back.')
    except OperationFailure as error:
        message = utils.get_error_message(error)
        if messages.NO_TRANSACTION_ERROR not in message:
            raise
    commands.begin()


def transaction_after_request(response):
    """Teardown transaction after handling the request. Rollback if an
    uncaught exception occurred, else commit. If the commit fails due to a lock
    error, rollback and return error response.
    """
    if view_has_annotation(NO_AUTO_TRANSACTION_ATTR):
        return response
    if response.status_code >= 500:
        commands.rollback()
    else:
        try:
            commands.commit()
        except OperationFailure as error:
            message = utils.get_error_message(error)
            if 'lock not granted' in message.lower():
                commands.rollback()
                return utils.handle_error(LOCK_ERROR_CODE)
            raise
    return response


def transaction_teardown_request(error=None):
    """Rollback transaction on uncaught error. This code should never be
    reached in debug mode, since uncaught errors are raised for use in the
    Werkzeug debugger.
    """
    if view_has_annotation(NO_AUTO_TRANSACTION_ATTR):
        return None
    if error is not None:
        if not settings.DEBUG_MODE:
            logger.error('Uncaught error in `transaction_teardown_request`; '
                         'this should never happen with `DEBUG_MODE = True`')
        # If we're testing, the before_request handlers may not have been executed
        # e.g. when Flask#test_request_context() is used
        if not current_app.testing:
            commands.rollback()


handlers = {
    'before_request': transaction_before_request,
    'after_request': transaction_after_request,
    'teardown_request': transaction_teardown_request,
}
