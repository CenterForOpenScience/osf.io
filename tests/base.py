# -*- coding: utf-8 -*-
'''Base TestCase class for OSF unittests. Uses a temporary MongoDB database.'''
import unittest
import logging
import functools
import blinker

from pymongo import MongoClient
from faker import Factory

from framework import storage, set_up_storage
from framework.auth import User
from framework.sessions.model import Session
from framework.guid.model import Guid
from website.project.model import (ApiKey, Node, NodeLog,
                                   Tag, WatchConfig)
from website import settings

from website.addons.osffiles.model import NodeFile
from website.addons.wiki.model import NodeWikiPage

import website.models
from website.signals import ALL_SIGNALS
from website.app import init_app
from website.util import web_url_for, api_url_for

# Just a simple app without routing set up or backends
test_app = init_app(
    settings_module='website.settings', routes=False, set_backends=False
)

# Silence some 3rd-party logging
SILENT_LOGGERS = ['factory.generate', 'factory.containers']
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

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
    db_host = getattr(settings, 'MONGO_HOST', 'localhost')
    db_port = int(getattr(settings, 'DB_PORT', '27017'))

    @classmethod
    def setUpClass(cls):
        '''Before running this TestCase, set up a temporary MongoDB database'''
        cls._client = MongoClient(host=cls.db_host, port=cls.db_port)
        cls.db = cls._client[cls.db_name]
        # Set storage backend to MongoDb
        set_up_storage(
            website.models.MODELS, storage.MongoStorage,
            addons=settings.ADDONS_AVAILABLE, db=cls.db,
        )
        cls._client.drop_database(cls.db)
        cls.context = test_app.test_request_context()
        cls.context.push()

    @classmethod
    def tearDownClass(cls):
        '''Drop the database when all tests finish.'''
        cls.context.pop()
        cls._client.drop_database(cls.db)


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
    blinker `NamedSignals` to patch. Each signal has it's `send` mocked out.
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


class URLLookup(object):
    """Utility class for doing reverse URL lookup within tests. Just wraps
    web_url_for and api_url_for so they can be used outside of app context.

    Usage: ::

        from website.app import init_app
        from tests.base import OsfTestCase, URLLookup

        app = init_app()
        lookup = URLLookup(app)

        class TestProjectViews(OsfTestCase):
            ...
            def test_project_endpoint(self):
                url = lookup('web', 'view_project', pid=self.project._primary_key)
    """

    def __init__(self, app):
        self.app = app

    def web_url_for(self, view_name, *args, **kwargs):
        with self.app.test_request_context():  # Need a request context to use url_for
            url = web_url_for(view_name, *args, **kwargs)
        return url

    def api_url_for(self, view_name, *args, **kwargs):
        with self.app.test_request_context():
            url = api_url_for(view_name, *args, **kwargs)
        return url

    def __call__(self, type_, view_name, *args, **kwargs):
        if type_ == 'web':
            return self.web_url_for(view_name, *args, **kwargs)
        else:
            return self.api_url_for(view_name, *args, **kwargs)

def assert_is_redirect(response, msg="Response is a redirect."):
    assert 300 <= response.status_code < 400, msg
