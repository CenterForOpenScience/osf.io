# -*- coding: utf-8 -*-

import httplib
import logging
from pymongo.errors import OperationFailure

from framework.mongo import database
from framework.flask import add_handler

from website import settings


logger = logging.getLogger(__name__)


def transaction_before_request():
    """Setup transaction before handling the request.

    """
    try:
        database.command('rollbackTransaction')
        logger.error('Transaction already in progress; rolling back.')
    except OperationFailure as error:
        message = ''
        try:
            message = error.args[0]
        except IndexError:
            pass
        if 'no transaction exists to be rolled back' not in message:
            raise
    database.command('beginTransaction')


def transaction_after_request(response):
    """Teardown transaction after handling the request. Rollback if an
    uncaught exception occurred, else commit.

    """
    if response.status_code == httplib.INTERNAL_SERVER_ERROR:
        database.command('rollbackTransaction')
    else:
        database.command('commitTransaction')
    return response


def transaction_teardown_request(error=None):
    """Rollback transaction on uncaught error. This code should never be
    reached in debug mode, since uncaught errors are raised for use in the
    Werkzeug debugger.

    """
    if error is not None:
        if not settings.DEBUG_MODE:
            logger.error('Uncaught error in `transaction_teardown_request`;'
                         'this should never happen with `DEBUG_MODE = True`')
        database.command('rollbackTransaction')


def add_transaction_handlers(app):
    """Add transaction callbacks on `before_request`, `after_request`, and
    `teardown_request`.

    """
    add_handler(app, 'before_request', transaction_before_request)
    add_handler(app, 'after_request', transaction_after_request)
    add_handler(app, 'teardown_request', transaction_teardown_request)
    #app.before_request(transaction_before_request)
    #app.after_request(transaction_after_request)
    #app.teardown_request(transaction_teardown_request)

