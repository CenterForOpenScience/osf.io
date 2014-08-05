# -*- coding: utf-8 -*-

import httplib
import logging
from pymongo.errors import OperationFailure

from framework.mongo import database

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


# TODO: What if transaction has already been rolled back or committed?
def transaction_after_request(response):
    """Teardown transaction after handling the request. Rollback if an
    uncaught exception occurred, else commit.

    """
    if response.status_code == httplib.INTERNAL_SERVER_ERROR:
        database.command('rollbackTransaction')
    else:
        # import pdb; pdb.set_trace()
        database.command('commitTransaction')
    return response


def transaction_teardown_request(error=None):
    """

    """
    if error is not None:
        if not settings.DEBUG_MODE:
            logger.error('THIS SHOULD NEVER HAPPEN')
        database.command('rollbackTransaction')


def add_transaction_handlers(app):
    """Add transaction callbacks on `before_request`, `after_request`, and
    `teardown_request`.

    """
    app.before_request(transaction_before_request)
    app.after_request(transaction_after_request)
    app.teardown_request(transaction_teardown_request)
