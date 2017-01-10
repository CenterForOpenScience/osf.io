# -*- coding: utf-8 -*-
import contextlib

import logging
from framework.mongo import database as proxy_database
from website import settings as osfsettings

logger = logging.getLogger(__name__)

@contextlib.contextmanager
def handle_missing_client():
    try:
        yield
    except AttributeError:
        if not osfsettings.DEBUG_MODE:
            logger.error('MongoDB client not attached to request.')

def begin(database=None):
    database = database or proxy_database
    with handle_missing_client():
        database.command('beginTransaction')

def rollback(database=None):
    database = database or proxy_database
    with handle_missing_client():
        database.command('rollbackTransaction')

def commit(database=None):
    database = database or proxy_database
    with handle_missing_client():
        database.command('commitTransaction')

def show_live(database=None):
    database = database or proxy_database
    with handle_missing_client():
        return database.command('showLiveTransactions')

def disconnect(database=None):
    database = database or proxy_database
    with handle_missing_client():
        database.connection.close()
