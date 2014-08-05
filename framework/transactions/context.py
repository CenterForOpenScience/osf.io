# -*- coding: utf-8 -*-

import logging
from pymongo.errors import OperationFailure

from framework.mongo import database


logger = logging.getLogger(__name__)


def begin_transaction_error(error):
    try:
        message = error.args[0]
    except IndexError:
        raise error
    if 'transaction already exists' not in message:
        raise error


class TokuTransaction(object):
    """Transaction context manager. Begin transaction on enter; rollback or
    commit on exit. TokuMX does not support nested transactions; catch and
    ignore attempts to nest transactions.

    """
    def __init__(self, database):
        self.database = database
        self.pending = False

    def __enter__(self):
        try:
            self.database.command('beginTransaction')
            self.pending = True
        except OperationFailure as error:
            begin_transaction_error(error)
            logger.warn('Transaction already in progress')
        finally:
            return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.pending:
            if exc_type:
                self.database.command('rollbackTransaction')
                raise exc_val
            self.database.command('commitTransaction')
            self.pending = False


def transaction(database=database):
    """Transaction decorator factory. Create a decorator that wraps the
    decorated function in a transaction using the provided database object.

    """
    def wrapper(func):
        def wrapped(*args, **kwargs):
            with TokuTransaction(database):
                return func(*args, **kwargs)
        return wrapped
    return wrapper
