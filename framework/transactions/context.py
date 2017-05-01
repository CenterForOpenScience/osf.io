# -*- coding: utf-8 -*-
import logging
import functools

from django.db import transaction as dj_transaction
from pymongo.errors import OperationFailure

from framework.mongo import database as proxy_database
from framework.transactions import commands, messages, utils
from website.settings import USE_POSTGRES

logger = logging.getLogger(__name__)


class TokuTransaction(object):
    """DEPRECATED. Transaction context manager. Begin transaction on enter; rollback or
    commit on exit. This behaves like `django.db.transaction.atomic` and exists only to
    support legacy code.

    This class is deprecated: use `django.db.transaction.atomic` instead.
    """
    def __init__(self, database=None):
        self.database = database or proxy_database
        self.pending = False
        if USE_POSTGRES:
            self.atomic = dj_transaction.atomic()

    def __enter__(self):
        if USE_POSTGRES:
            return self._django_enter()
        else:
            return self._modm_enter()

    def _django_enter(self):
        self.pending = True
        return self.atomic.__enter__()

    def _modm_enter(self):
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
        if USE_POSTGRES:
            return self._django_exit(exc_type, exc_val, exc_tb)
        else:
            return self._modm_exit(exc_type, exc_val, exc_tb)

    def _django_exit(self, exc_type, exc_val, exc_tb):
        self.pending = False
        return self.atomic.__exit__(exc_type, exc_val, exc_tb)

    def _modm_exit(self, exc_type, exc_val, exc_tb):
        if self.pending:
            if exc_type:
                commands.rollback(self.database)
                self.pending = False
                raise exc_type, exc_val, exc_tb
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
