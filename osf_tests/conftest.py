import logging

import pytest
from faker import Factory

from framework.django.handlers import handlers as django_handlers
from framework.flask import rm_handlers
from website import settings as osf_settings
from website.app import init_app
from website.project.signals import contributor_added
from website.project.views.contributor import notify_added_contributor
from website import search
from website.search.drivers.disabled import SearchDisabledDriver

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
    'transitions.core',
    'MARKDOWN',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


# NOTE: autouse so that ADDONS_REQUESTED gets set on website.settings
@pytest.fixture(autouse=True, scope='session')
def app():
    try:
        test_app = init_app(routes=True, set_backends=False)
    except AssertionError:  # Routes have already been set up
        test_app = init_app(routes=False, set_backends=False)

    rm_handlers(test_app, django_handlers)

    test_app.testing = True
    return test_app


@pytest.yield_fixture()
def request_context(app):
    context = app.test_request_context(headers={
        'Remote-Addr': '146.9.219.56',
        'User-Agent': 'Mozilla/5.0 (X11; U; SunOS sun4u; en-US; rv:0.9.4.1) Gecko/20020518 Netscape6/6.2.3'
    })
    context.push()
    yield context
    context.pop()

DISCONNECTED_SIGNALS = {
    # disconnect notify_add_contributor so that add_contributor does not send "fake" emails in tests
    contributor_added: [notify_added_contributor]
}
@pytest.fixture(autouse=True)
def disconnected_signals():
    for signal in DISCONNECTED_SIGNALS:
        for receiver in DISCONNECTED_SIGNALS[signal]:
            signal.disconnect(receiver)

@pytest.fixture(autouse=True)
def patched_settings():
    """Patch settings for tests"""
    osf_settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
    osf_settings.BCRYPT_LOG_ROUNDS = 1

@pytest.fixture()
def fake():
    return Factory.create()

@pytest.fixture(autouse=True)
def settings(settings):
    settings.TEST_OPTIONS.update(settings.DEFAULT_TEST_OPTIONS)
    yield settings
    settings.TEST_OPTIONS.update(settings.DEFAULT_TEST_OPTIONS)


@pytest.fixture
def enable_quickfiles_creation(settings):
    settings.TEST_OPTIONS.DISABLE_QUICK_FILES_CREATION = False


@pytest.fixture
def enable_bookmark_creation(settings):
    settings.TEST_OPTIONS.DISABLE_BOOKMARK_COLLECTION_CREATION = False


@pytest.fixture
def enable_implicit_clean(settings):
    settings.TEST_OPTIONS.DISABLE_IMPLICIT_FULL_CLEAN = False


@pytest.fixture
def enable_enqueue_task(settings):
    settings.TEST_OPTIONS.DISABLE_ENQUEUE_TASK = False


@pytest.fixture(autouse=True)
def disable_search():
    search.search = SearchDisabledDriver(warnings=False)
