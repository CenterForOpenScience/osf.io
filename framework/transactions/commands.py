# -*- coding: utf-8 -*-

from pymongo.errors import OperationFailure

from framework.mongo import database as proxy_database
from flask import current_app

from website import settings

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
