# -*- coding: utf-8 -*-
'''Base TestCase class for OSF unittests. Uses a temporary MongoDB database.'''
import mock
import unittest
import logging
import functools
import blinker
from webtest_plus import TestApp

from pymongo import MongoClient
from faker import Factory

from framework.mongo import storage, set_up_storage
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


class DbTestCase(unittest.TestCase):
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

    def setUp(self):
        self.app = TestApp(test_app)
        self.context = test_app.test_request_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    @classmethod
    def tearDownClass(cls):
        '''Drop the database when all tests finish.'''
        cls._client.drop_database(cls.db)


class OsfTestCase(DbTestCase):

    PATCH_GITLAB = True

    @classmethod
    def setUpClass(cls):
        super(OsfTestCase, cls).setUpClass()
        if cls.PATCH_GITLAB:
            cls.start_gitlab_patches()

    @classmethod
    def tearDownClass(cls):
        super(OsfTestCase, cls).tearDownClass()
        if cls.PATCH_GITLAB:
            mock.patch.stopall()

    @classmethod
    def start_gitlab_patches(cls):
        edit_user_patch = mock.patch(
            'website.addons.gitlab.services.userservice.GitlabUserService.edit'
        )
        edit_user_mock = edit_user_patch.start()
        edit_user_mock.return_value = {}

        create_patch = mock.patch(
            'website.addons.gitlab.services.userservice.GitlabUserService.create'
        )
        create_mock = create_patch.start()
        create_mock.return_value = {
            'id': 1,
            'username': 'Roger',
        }

        setup_user_patch = mock.patch(
            'website.addons.gitlab.model.setup_user'
        )
        setup_user_mock = setup_user_patch.start()
        setup_user_rv = mock.Mock()
        setup_user_rv.user_id = 1
        setup_user_mock.return_value = setup_user_rv

        add_member_patch = mock.patch(
            'website.addons.gitlab.services.projectservice.GitlabProjectService.add_member'
        )
        add_member_mock = add_member_patch.start()
        add_member_mock.return_value = True

        edit_member_patch = mock.patch(
            'website.addons.gitlab.services.projectservice.GitlabProjectService.edit_member'
        )
        edit_member_mock = edit_member_patch.start()
        edit_member_mock.return_value = True

        copy_patch = mock.patch(
            'website.addons.gitlab.services.projectservice.GitlabProjectService.copy'
        )
        copy_mock = copy_patch.start()
        copy_mock.return_value = {'id': 1}

        branches_patch = mock.patch(
            'website.addons.gitlab.services.fileservice.GitlabFileService.list_branches'
        )
        branches_mock = branches_patch.start()
        branches_mock.return_value = [
            {
                'name': 'master',
                'commit': {
                    'id': '0c015ac47ee16eb0fc17c0a6417d57622bbf142d',
                }
            }
        ]


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


def assert_is_redirect(response, msg="Response is a redirect."):
    assert 300 <= response.status_code < 400, msg
