# -*- coding: utf-8 -*-
'''Base TestCase class for OSF unittests. Uses a temporary MongoDB database.'''
import unittest
import logging
import functools
import blinker
from webtest_plus import TestApp

from faker import Factory
from pymongo.errors import OperationFailure
from modularodm import storage

from framework.mongo import set_up_storage
from framework.auth import User
from framework.sessions.model import Session
from framework.guid.model import Guid
from framework.mongo import client, database
from framework.transactions import commands, messages, utils

from website.project.model import (
    ApiKey, Node, NodeLog, Tag, WatchConfig,
)
from website import settings

from website.addons.osffiles.model import NodeFile
from website.addons.wiki.model import NodeWikiPage

import website.models
from website.signals import ALL_SIGNALS
from website.app import init_app

# Just a simple app without routing set up or backends
test_app = init_app(
    settings_module='website.settings', routes=True, set_backends=False
)


logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)

# Silence some 3rd-party logging and some "loud" internal loggers
SILENT_LOGGERS = [
    'factory.generate',
    'factory.containers',
    'website.search.elastic_search',
    'framework.auth.core',
    'website.mails',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Fake factory
fake = Factory.create()

# All Models
MODELS = (User, ApiKey, Node, NodeLog, NodeFile, NodeWikiPage,
          Tag, WatchConfig, Session, Guid)


class OsfTestCase(unittest.TestCase):
    '''Base TestCase for tests that require a temporary MongoDB database.
    '''
    # DB settings
    db_name = getattr(settings, 'TEST_DB_NAME', 'osf_test')

    @classmethod
    def setUpClass(cls):
        """Clear test database and attach to schema classes.

        """
        cls._original_db, settings.DB_NAME = settings.DB_NAME, cls.db_name
        set_up_storage(
            website.models.MODELS,
            storage.MongoStorage,
            addons=settings.ADDONS_AVAILABLE,
        )
        client.drop_database(cls.db_name)

    def setUp(self):
        self.app = TestApp(test_app)
        self.context = test_app.test_request_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    @classmethod
    def tearDownClass(cls):
        """Clear test database again.

        """
        client.drop_database(cls.db_name)
        settings.DB_NAME = cls._original_db


def teardown_database(client=client, database=database):
    try:
        commands.rollback(database)
    except OperationFailure as error:
        message = utils.get_error_message(error)
        if messages.NO_TRANSACTION_ERROR not in message:
            raise
    client.drop_database(database)


class DbTestCase(unittest.TestCase):

    DB_NAME = getattr(settings, 'TEST_DB_NAME', 'osf_test')

    @classmethod
    def setUpClass(cls):
        cls._original_db_name = settings.DB_NAME
        settings.DB_NAME = cls.DB_NAME
        teardown_database(database=database._get_current_object())

    @classmethod
    def tearDownClass(cls):
        teardown_database(database=database._get_current_object())
        settings.DB_NAME = cls._original_db_name


class AppTestCase(unittest.TestCase):
    '''Base TestCase for OSF tests that require the WSGI app (but no database).
    '''

    def setUp(self):
        self.app = test_app
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()


# From Flask-Security: https://github.com/mattupstate/flask-security/blob/develop/flask_security/utils.py
class CaptureSignals(object):
    """Testing utility for capturing blinker signals.

    Context manager which mocks out selected signals and registers which
    are `sent` on and what arguments were sent. Instantiate with a list of
    blinker `NamedSignals` to patch. Each signal has its `send` mocked out.

    """
    def __init__(self, signals):
        """Patch all given signals and make them available as attributes.

        :param signals: list of signals

        """
        self._records = {}
        self._receivers = {}
        for signal in signals:
            self._records[signal] = []
            self._receivers[signal] = functools.partial(self._record, signal)

    def __getitem__(self, signal):
        """All captured signals are available via `ctxt[signal]`.
        """
        if isinstance(signal, blinker.base.NamedSignal):
            return self._records[signal]
        else:
            super(CaptureSignals, self).__setitem__(signal)

    def _record(self, signal, *args, **kwargs):
        self._records[signal].append((args, kwargs))

    def __enter__(self):
        for signal, receiver in self._receivers.items():
            signal.connect(receiver)
        return self

    def __exit__(self, type, value, traceback):
        for signal, receiver in self._receivers.items():
            signal.disconnect(receiver)

    def signals_sent(self):
        """Return a set of the signals sent.
        :rtype: list of blinker `NamedSignals`.

        """
        return set([signal for signal, _ in self._records.items() if self._records[signal]])


def capture_signals():
    """Factory method that creates a ``CaptureSignals`` with all OSF signals."""
    return CaptureSignals(ALL_SIGNALS)


def assert_is_redirect(response, msg="Response is a redirect."):
    assert 300 <= response.status_code < 400, msg

