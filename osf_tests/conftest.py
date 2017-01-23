import logging

import pytest
from faker import Factory

from framework.django.handlers import handlers as django_handlers
from framework.flask import rm_handlers
from website import settings
from website.app import init_app, patch_models
from website.project.signals import contributor_added
from website.project.views.contributor import notify_added_contributor

# Silence some 3rd-party logging and some "loud" internal loggers
SILENT_LOGGERS = [
    'factory.generate',
    'factory.containers',
    'website.search.elastic_search',
    'framework.analytics',
    'framework.auth.core',
    'website.mails',
    'website.search_migration.migrate',
    'website.util.paths',
    'api.caching.tasks',
    'website.notifications.listeners',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


@pytest.fixture(autouse=True, scope='session')
def patched_models():
    patch_models(settings)


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
    settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
    settings.BCRYPT_LOG_ROUNDS = 1

@pytest.fixture()
def fake():
    return Factory.create()
