# -*- coding: utf-8 -*-

import httplib
import logging

import sys
from flask import request, current_app
from pymongo.errors import OperationFailure

from framework.transactions import utils, commands, messages


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


def transaction_after_request(response, base_status_code_error=500):
    """Teardown transaction after handling the request. Rollback if an
    uncaught exception occurred, else commit. If the commit fails due to a lock
    error, rollback and return error response.
    """
    if view_has_annotation(NO_AUTO_TRANSACTION_ATTR):
        return response
    if response.status_code >= base_status_code_error:
        original_exception = sys.exc_info()
        try:
            commands.rollback()
        except OperationFailure:
            logger.error(original_exception, exc_info=1)
            return response
        else:
            return response
    else:
        try:
            commands.commit()
        except OperationFailure as error:
            message = utils.get_error_message(error)
            if messages.LOCK_ERROR in message:
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
        return
    if error is not None:
        try:
            commands.rollback()
        except OperationFailure as error:
            message = utils.get_error_message(error)
            if messages.NO_TRANSACTION_ERROR not in message:
                raise


handlers = {
    'before_request': transaction_before_request,
    'after_request': transaction_after_request,
    'teardown_request': transaction_teardown_request,
}
