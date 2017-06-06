import logging
import pytest

from tests.json_api_test_app import JSONAPITestApp

# Silence some 3rd-party logging and some "loud" internal loggers
SILENT_LOGGERS = [
    'api.caching.tasks',
    'factory.generate',
    'factory.containers',
    'framework.analytics',
    'framework.auth.core',
    'framework.celery_tasks.signals',
    'website.app',
    'website.archiver.tasks',
    'website.mails',
    'website.notifications.listeners',
    'website.search.elastic_search',
    'website.search_migration.migrate',
    'website.util.paths',
    'osf.migrations',
    'osf.models',
    'addons.osfstorage.models',
    'rest_framework.pagination',
    'tests.base',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

@pytest.fixture()
def app():
    return JSONAPITestApp()
