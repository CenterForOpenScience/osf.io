# -*- coding: utf-8 -*-

from framework.mongo import database as proxy_database
from pymongo.errors import OperationFailure


def begin(database=None):
    database = database or proxy_database
    database.command('beginTransaction')


def rollback(database=None):
    database = database or proxy_database
    try:
        database.command('rollbackTransaction')
    except OperationFailure:
        pass


def commit(database=None):
    database = database or proxy_database
    database.command('commitTransaction')


def show_live(database=None):
    database = database or proxy_database
    return database.command('showLiveTransactions')
