import logging

import pytest
from faker import Factory

from website import settings
from website.app import patch_models
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
    'api.caching.tasks'
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


@pytest.fixture(autouse=True)
def patched_models():
    patch_models(settings)


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
