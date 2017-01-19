import logging

import pytest

from website.app import init_app

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

# NOTE: autouse so that ADDONS_REQUESTED gets set on website.settings
@pytest.fixture(autouse=True, scope='session')
def app():
    try:
        test_app = init_app(routes=True, set_backends=False, attach_django_backends=False)
    except AssertionError:  # Routes have already been set up
        test_app = init_app(routes=False, set_backends=False, attach_django_backends=False)
    test_app.testing = True
    return test_app
