# -*- coding: utf-8 -*-

from pymongo.errors import OperationFailure

from framework.mongo import database as proxy_database

from website import settings

def begin(database=None):
    database = database or proxy_database
    database.command('beginTransaction')


def rollback(database=None):
    database = database or proxy_database
    try:
        # This method is called by various request teardown handlers, and can
        #   interfere with tests - specifically those which use a test request
        #   context, as in some cases the handlers used to initiate the TokuMX
        #   transaction before the request is processed are not called.
        #
        # The most common issue with this is an extra traceback in the test
        #   runner output when a test fails. Less common, tests that use Flask's
        #   native Flask#test_request_context may fail when they would otherwise
        #   pass
        #
        # ref: http://flask.pocoo.org/docs/0.10/reqcontext/
        #   "Make sure to write your teardown-request handlers in a way that
        #    they will never fail."
        database.command('rollbackTransaction')
    except OperationFailure:
        # Re-raise the exception if not in debug mode. This allows
        #   exceptions on staging to be handled in the same way as those on
        #   production, while also allowing tests to be run without this
        #   exception being raised
        if not settings.DEBUG_MODE:
            raise


def commit(database=None):
    database = database or proxy_database
    database.command('commitTransaction')


def show_live(database=None):
    database = database or proxy_database
    return database.command('showLiveTransactions')
