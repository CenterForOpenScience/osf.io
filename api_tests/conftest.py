import logging
import pytest
from faker import Factory

from osf_tests.conftest import *  # noqa
from osf_tests.conftest import _elasticsearch  # noqa
from website.app import init_app
from tests.json_api_test_app import JSONAPITestApp

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
    'transitions.core',
    'MARKDOWN',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)


# @pytest.fixture(scope='session')
@pytest.fixture()
def app():
    return JSONAPITestApp()

# NOTE: autouse so that ADDONS_REQUESTED gets set on website.settings
@pytest.fixture(autouse=True, scope='session')
def app_init():
    init_app(routes=False, set_backends=False)


@pytest.fixture()
def fake():
    return Factory.create()

# Used to disable osf_tests disconnected_signals
def disconnected_signals():
    pass
