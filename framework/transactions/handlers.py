# -*- coding: utf-8 -*-

import httplib
import logging

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
        logger.error('Transaction already in progress prior to request; rolling back.')
    except OperationFailure as error:
        #  expected error, transaction shouldn't be started prior to request
        message = utils.get_error_message(error)
        if messages.NO_TRANSACTION_ERROR not in message:
            #  exception not a transaction error, reraise
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
        try:
            commands.rollback()
        except OperationFailure:
            logger.exception('Transaction rollback failed after request')
    else:
        try:
            commands.commit()
        except OperationFailure as error:
            #  transaction commit failed, log and reraise
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
            #  expected error, transaction should have closed in after_request
            message = utils.get_error_message(error)
            if messages.NO_TRANSACTION_ERROR not in message:
                #  unexpected error, not a transaction error, reraise
                raise


handlers = {
    'before_request': transaction_before_request,
    'after_request': transaction_after_request,
    'teardown_request': transaction_teardown_request,
}
