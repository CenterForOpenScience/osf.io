# -*- coding: utf-8 -*-
'''Base TestCase class for OSF unittests. Uses a temporary MongoDB database.'''
import datetime as dt
import functools
import logging
import os
import shutil
import unittest
import mock

from webtest_plus import TestApp
import blinker

from faker import Factory
from nose.tools import *  # noqa (PEP8 asserts)
from pymongo.errors import OperationFailure
from modularodm import storage

from framework.mongo import set_up_storage
from framework.auth import User
from framework.sessions.model import Session
from framework.guid.model import Guid
from framework.mongo import client as client_proxy
from framework.mongo import database as database_proxy
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

from tests.exceptions import UnmockedError

# Just a simple app without routing set up or backends
test_app = init_app(
    settings_module='website.settings', routes=True, set_backends=False
)
test_app.testing = True


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


def teardown_database(client=None, database=None):
    client = client or client_proxy
    database = database or database_proxy
    if settings.USE_TOKU_MX:
        try:
            commands.rollback(database)
        except OperationFailure as error:
            message = utils.get_error_message(error)
            if messages.NO_TRANSACTION_ERROR not in message:
                raise
    client.drop_database(database)


class DbTestCase(unittest.TestCase):
    """Base `TestCase` for tests that require a scratch database.
    """
    DB_NAME = getattr(settings, 'TEST_DB_NAME', 'osf_test')

    @classmethod
    def setUpClass(cls):
        super(DbTestCase, cls).setUpClass()

        cls._original_db_name = settings.DB_NAME
        settings.DB_NAME = cls.DB_NAME
        cls._original_piwik_host = settings.PIWIK_HOST
        settings.PIWIK_HOST = None
        cls._original_enable_email_subscriptions = settings.ENABLE_EMAIL_SUBSCRIPTIONS
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False

        teardown_database(database=database_proxy._get_current_object())
        # TODO: With `database` as a `LocalProxy`, we should be able to simply
        # this logic
        set_up_storage(
            website.models.MODELS,
            storage.MongoStorage,
            addons=settings.ADDONS_AVAILABLE,
        )
        cls.db = database_proxy

    @classmethod
    def tearDownClass(cls):
        super(DbTestCase, cls).tearDownClass()
        teardown_database(database=database_proxy._get_current_object())
        settings.DB_NAME = cls._original_db_name
        settings.PIWIK_HOST = cls._original_piwik_host
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = cls._original_enable_email_subscriptions


class AppTestCase(unittest.TestCase):
    """Base `TestCase` for OSF tests that require the WSGI app (but no database).
    """
    def setUp(self):
        super(AppTestCase, self).setUp()
        self.app = TestApp(test_app)
        self.context = test_app.test_request_context()
        self.context.push()

    def tearDown(self):
        super(AppTestCase, self).tearDown()
        self.context.pop()


class UploadTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Store uploads in temp directory.
        """
        super(UploadTestCase, cls).setUpClass()
        cls._old_uploads_path = settings.UPLOADS_PATH
        cls._uploads_path = os.path.join('/tmp', 'osf', 'uploads')
        try:
            os.makedirs(cls._uploads_path)
        except OSError:  # Path already exists
            pass
        settings.UPLOADS_PATH = cls._uploads_path

    @classmethod
    def tearDownClass(cls):
        """Restore uploads path.
        """
        super(UploadTestCase, cls).tearDownClass()
        shutil.rmtree(cls._uploads_path)
        settings.UPLOADS_PATH = cls._old_uploads_path


class MockRequestTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(MockRequestTestCase, cls).setUpClass()
        mock.patch('requests.Session.send', side_effect=UnmockedError).start()


class OsfTestCase(DbTestCase, AppTestCase, UploadTestCase, MockRequestTestCase):
    """Base `TestCase` for tests that require both scratch databases and the OSF
    application. Note: superclasses must call `super` in order for all setup and
    teardown methods to be called correctly.
    """
    pass


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


def assert_before(lst, item1, item2):
    """Assert that item1 appears before item2 in lst."""
    assert_less(lst.index(item1), lst.index(item2),
        '{0!r} appears before {1!r}'.format(item1, item2))


def assert_datetime_equal(dt1, dt2, allowance=500):
    """Assert that two datetimes are about equal."""
    assert_less(dt1 - dt2, dt.timedelta(milliseconds=allowance))
