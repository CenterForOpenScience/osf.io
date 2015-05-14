# -*- coding: utf-8 -*-
import logging
from framework.mongo import database as proxy_database
from website import settings as osfsettings

logger = logging.getLogger(__name__)


def begin(database=None):
    database = database or proxy_database
    database.command('beginTransaction')


def rollback(database=None):
    database = database or proxy_database
    database.command('rollbackTransaction')


def commit(database=None):
    database = database or proxy_database
    database.command('commitTransaction')


def show_live(database=None):
    database = database or proxy_database
    return database.command('showLiveTransactions')


def disconnect(database=None):
    database = database or proxy_database
    try:
        database.connection.close()
    except AttributeError:
        if not osfsettings.DEBUG_MODE:
            logger.error('MongoDB client not attached to request.')