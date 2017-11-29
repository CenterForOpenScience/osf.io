# -*- coding: utf-8 -*-
'''Base TestCase class for OSF unittests. Uses a temporary MongoDB database.'''
import abc
import datetime as dt
import functools
import logging
import re
import unittest
import uuid

import blinker
import httpretty
import mock
import pytest

from django.test import TestCase as DjangoTestCase
from django.test import override_settings
from faker import Factory
from framework.auth.core import Auth
from framework.celery_tasks.handlers import celery_before_request
from framework.django.handlers import handlers as django_handlers
from framework.flask import rm_handlers
from osf.models import MetaSchema
from website import settings
from website.app import init_app
from website.notifications.listeners import (subscribe_contributor,
                                             subscribe_creator)
from website.project.signals import contributor_added, project_created
from website.project.views.contributor import notify_added_contributor
from website.signals import ALL_SIGNALS
from webtest_plus import TestApp

from .json_api_test_app import JSONAPITestApp

from nose.tools import *  # noqa (PEP8 asserts); noqa (PEP8 asserts)

logger = logging.getLogger(__name__)


def get_default_metaschema():
    """This needs to be a method so it gets called after the test database is set up"""
    return MetaSchema.objects.first()

try:
    test_app = init_app(routes=True, set_backends=False)
except AssertionError:  # Routes have already been set up
    test_app = init_app(routes=False, set_backends=False)

rm_handlers(test_app, django_handlers)

test_app.testing = True


# Silence some 3rd-party logging and some "loud" internal loggers
SILENT_LOGGERS = [
    'api.caching.tasks',
    'factory.generate',
    'factory.containers',
    'framework.analytics',
    'framework.auth.core',
    'website.app',
    'website.archiver.tasks',
    'website.mails',
    'website.notifications.listeners',
    'website.search.elastic_search',
    'website.search_migration.migrate',
    'website.util.paths',
    'requests_oauthlib.oauth2_session',
    'raven.base.Client',
    'raven.contrib.django.client.DjangoClient',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

# Fake factory
fake = Factory.create()


@pytest.mark.django_db
class DbTestCase(unittest.TestCase):
    """Base `TestCase` for tests that require a scratch database.
    """
    @classmethod
    def setUpClass(cls):
        super(DbTestCase, cls).setUpClass()

        cls._original_enable_email_subscriptions = settings.ENABLE_EMAIL_SUBSCRIPTIONS
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = False

        cls._original_bcrypt_log_rounds = settings.BCRYPT_LOG_ROUNDS
        settings.BCRYPT_LOG_ROUNDS = 4

    @classmethod
    def tearDownClass(cls):
        super(DbTestCase, cls).tearDownClass()
        settings.ENABLE_EMAIL_SUBSCRIPTIONS = cls._original_enable_email_subscriptions
        settings.BCRYPT_LOG_ROUNDS = cls._original_bcrypt_log_rounds


class AppTestCase(unittest.TestCase):
    """Base `TestCase` for OSF tests that require the WSGI app (but no database).
    """

    PUSH_CONTEXT = True
    DISCONNECTED_SIGNALS = {
        # disconnect notify_add_contributor so that add_contributor does not send "fake" emails in tests
        contributor_added: [notify_added_contributor]
    }

    def setUp(self):
        super(AppTestCase, self).setUp()
        self.app = TestApp(test_app)
        if not self.PUSH_CONTEXT:
            return
        self.context = test_app.test_request_context(headers={
            'Remote-Addr': '146.9.219.56',
            'User-Agent': 'Mozilla/5.0 (X11; U; SunOS sun4u; en-US; rv:0.9.4.1) Gecko/20020518 Netscape6/6.2.3'
        })
        self.context.push()
        with self.context:
            celery_before_request()
        for signal in self.DISCONNECTED_SIGNALS:
            for receiver in self.DISCONNECTED_SIGNALS[signal]:
                signal.disconnect(receiver)

    def tearDown(self):
        super(AppTestCase, self).tearDown()
        if not self.PUSH_CONTEXT:
            return
        with mock.patch('website.mailchimp_utils.get_mailchimp_api'):
            self.context.pop()
        for signal in self.DISCONNECTED_SIGNALS:
            for receiver in self.DISCONNECTED_SIGNALS[signal]:
                signal.connect(receiver)


class ApiAppTestCase(unittest.TestCase):
    """Base `TestCase` for OSF API v2 tests that require the WSGI app (but no database).
    """
    allow_database_queries = True

    def setUp(self):
        super(ApiAppTestCase, self).setUp()
        self.app = JSONAPITestApp()


class SearchTestCase(unittest.TestCase):

    def setUp(self):
        settings.ELASTIC_INDEX = uuid.uuid4().hex
        settings.ELASTIC_TIMEOUT = 60

        from website.search import elastic_search
        elastic_search.INDEX = settings.ELASTIC_INDEX
        elastic_search.create_index(settings.ELASTIC_INDEX)

        # NOTE: Super is called last to ensure the ES connection can be established before
        #       the httpretty module patches the socket.
        super(SearchTestCase, self).setUp()

    def tearDown(self):
        super(SearchTestCase, self).tearDown()

        from website.search import elastic_search
        elastic_search.delete_index(settings.ELASTIC_INDEX)


methods = [
    httpretty.GET,
    httpretty.PUT,
    httpretty.HEAD,
    httpretty.POST,
    httpretty.PATCH,
    httpretty.DELETE,
]
def kill(*args, **kwargs):
    logger.error('httppretty.kill: %s - %s', args, kwargs)
    raise httpretty.errors.UnmockedError()


class MockRequestTestCase(unittest.TestCase):

    DISABLE_OUTGOING_CONNECTIONS = False

    def setUp(self):
        super(MockRequestTestCase, self).setUp()
        if self.DISABLE_OUTGOING_CONNECTIONS:
            httpretty.enable()
            for method in methods:
                httpretty.register_uri(
                    method,
                    re.compile(r'.*'),
                    body=kill,
                    priority=-1,
                )

    def tearDown(self):
        super(MockRequestTestCase, self).tearDown()
        httpretty.reset()
        httpretty.disable()


class OsfTestCase(DbTestCase, AppTestCase, SearchTestCase, MockRequestTestCase):
    """Base `TestCase` for tests that require both scratch databases and the OSF
    application. Note: superclasses must call `super` in order for all setup and
    teardown methods to be called correctly.
    """
    pass


class ApiTestCase(DbTestCase, ApiAppTestCase, SearchTestCase, MockRequestTestCase):
    """Base `TestCase` for tests that require both scratch databases and the OSF
    API application. Note: superclasses must call `super` in order for all setup and
    teardown methods to be called correctly.
    """
    def setUp(self):
        super(ApiTestCase, self).setUp()
        settings.USE_EMAIL = False

class ApiAddonTestCase(ApiTestCase):
    """Base `TestCase` for tests that require interaction with addons.

    """
    DISABLE_OUTGOING_CONNECTIONS = True

    @abc.abstractproperty
    def short_name(self):
        pass

    @abc.abstractproperty
    def addon_type(self):
        pass

    @abc.abstractmethod
    def _apply_auth_configuration(self):
        pass

    @abc.abstractmethod
    def _set_urls(self):
        pass

    def _settings_kwargs(self, node, user_settings):
        return {
            'user_settings': self.user_settings,
            'folder_id': '1234567890',
            'owner': self.node
        }

    def setUp(self):
        super(ApiAddonTestCase, self).setUp()
        from osf_tests.factories import (
            ProjectFactory,
            AuthUserFactory,
        )
        from addons.base.models import (
            BaseOAuthNodeSettings,
            BaseOAuthUserSettings
        )
        assert self.addon_type in ('CONFIGURABLE', 'OAUTH', 'UNMANAGEABLE', 'INVALID')
        self.account = None
        self.node_settings = None
        self.user_settings = None
        self.user = AuthUserFactory()
        self.auth = Auth(self.user)
        self.node = ProjectFactory(creator=self.user)

        if self.addon_type not in ('UNMANAGEABLE', 'INVALID'):
            if self.addon_type in ('OAUTH', 'CONFIGURABLE'):
                self.account = self.AccountFactory()
                self.user.external_accounts.add(self.account)
                self.user.save()

            self.user_settings = self.user.get_or_add_addon(self.short_name)
            self.node_settings = self.node.get_or_add_addon(self.short_name, auth=self.auth)

            if self.addon_type in ('OAUTH', 'CONFIGURABLE'):
                self.node_settings.set_auth(self.account, self.user)
                self._apply_auth_configuration()

        if self.addon_type in ('OAUTH', 'CONFIGURABLE'):
            assert isinstance(self.node_settings, BaseOAuthNodeSettings)
            assert isinstance(self.user_settings, BaseOAuthUserSettings)
            self.node_settings.reload()
            self.user_settings.reload()

        self.account_id = self.account._id if self.account else None
        self.set_urls()

    def tearDown(self):
        super(ApiAddonTestCase, self).tearDown()
        self.user.remove()
        self.node.remove()
        if self.node_settings:
            self.node_settings.remove()
        if self.user_settings:
            self.user_settings.remove()
        if self.account:
            self.account.remove()


@override_settings(ROOT_URLCONF='admin.base.urls')
class AdminTestCase(DbTestCase, DjangoTestCase, SearchTestCase, MockRequestTestCase):
    pass

class NotificationTestCase(OsfTestCase):
    """An `OsfTestCase` to use when testing specific subscription behavior.
    Use when you'd like to manually create all Node subscriptions and subscriptions
    for added contributors yourself, and not rely on automatically added ones.
    """
    DISCONNECTED_SIGNALS = {
        # disconnect signals so that add_contributor does not send "fake" emails in tests
        contributor_added: [notify_added_contributor, subscribe_contributor],
        project_created: [subscribe_creator]
    }

    def setUp(self):
        super(NotificationTestCase, self).setUp()

    def tearDown(self):
        super(NotificationTestCase, self).tearDown()


class ApiWikiTestCase(ApiTestCase):

    def setUp(self):
        from osf_tests.factories import AuthUserFactory
        super(ApiWikiTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.non_contributor = AuthUserFactory()

    def _add_project_wiki_page(self, node, user):
        from addons.wiki.tests.factories import NodeWikiFactory
        # API will only return current wiki pages
        # Mock out update_search. TODO: Remove when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            return NodeWikiFactory(node=node, user=user)

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

def assert_dict_contains_subset(a, b):
    assert set(a.items()).issubset(set(b.items()))

def assert_is_redirect(response, msg='Response is a redirect.'):
    assert 300 <= response.status_code < 400, msg


def assert_before(lst, item1, item2):
    """Assert that item1 appears before item2 in lst."""
    assert_less(lst.index(item1), lst.index(item2),
        '{0!r} appears before {1!r}'.format(item1, item2))

def assert_datetime_equal(dt1, dt2, allowance=500):
    """Assert that two datetimes are about equal."""

    assert abs(dt1 - dt2) < dt.timedelta(milliseconds=allowance)
