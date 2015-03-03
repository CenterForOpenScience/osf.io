# -*- coding: utf-8 -*-

import logging
import functools

from pymongo.errors import OperationFailure

from framework.mongo import database as proxy_database
from framework.transactions import commands, messages, utils


logger = logging.getLogger(__name__)


class TokuTransaction(object):
    """Transaction context manager. Begin transaction on enter; rollback or
    commit on exit. TokuMX does not support nested transactions; catch and
    ignore attempts to nest transactions.
    """
    def __init__(self, database=None):
        self.database = database or proxy_database
        self.pending = False

    def __enter__(self):
        try:
            commands.begin(self.database)
            self.pending = True
        except OperationFailure as error:
            message = utils.get_error_message(error)
            if messages.TRANSACTION_EXISTS_ERROR not in message:
                raise
            logger.warn('Transaction already in progress')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pending:
            if exc_type:
                commands.rollback(self.database)
                self.pending = False
                raise exc_val
            try:
                commands.commit(self.database)
                self.pending = False
            except OperationFailure as error:
                message = utils.get_error_message(error)
                if messages.LOCK_ERROR in message:
                    commands.rollback(self.database)
                    self.pending = False
                raise


def transaction(database=None):
    """Transaction decorator factory. Create a decorator that wraps the
    decorated function in a transaction using the provided database object.
    """
    def wrapper(func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            with TokuTransaction(database):
                return func(*args, **kwargs)
        return wrapped
    return wrapper
