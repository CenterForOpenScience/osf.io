# -*- coding: utf-8 -*-
import logging
import functools
from django.db import transaction as dj_transaction

from framework.mongo import database as proxy_database


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
        self.atomic = dj_transaction.atomic()

    def __enter__(self):
        self.pending = True
        return self.atomic.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pending = False
        return self.atomic.__exit__(exc_type, exc_val, exc_tb)


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
