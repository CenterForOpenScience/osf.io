import logging

import mock
import pytest
from faker import Factory
from website import settings as website_settings

from framework.celery_tasks import app as celery_app

logger = logging.getLogger(__name__)

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
    'elasticsearch',
]
for logger_name in SILENT_LOGGERS:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for the test environment.
    """
    # Make tasks run synchronously, and make sure exceptions get propagated
    celery_app.conf.update({
        'task_always_eager': True,
        'task_eager_propagates': True,
    })
    website_settings.ENABLE_EMAIL_SUBSCRIPTIONS = False
    # TODO: Remove if this is unused?
    website_settings.BCRYPT_LOG_ROUNDS = 1
    # Make sure we don't accidentally send any emails
    website_settings.SENDGRID_API_KEY = None
    # Set this here instead of in SILENT_LOGGERS, in case developers
    # call setLevel in local.py
    logging.getLogger('website.mails.mails').setLevel(logging.CRITICAL)


@pytest.fixture()
def fake():
    return Factory.create()

_MOCKS = {
    'osf.models.user.new_bookmark_collection': {
        'mark': 'enable_bookmark_creation',
        'replacement': lambda *args, **kwargs: None,
    },
    'osf.quickfiles.signals._create_quickfiles': {
        'mark': 'enable_quickfiles_creation',
        'replacement': lambda *args, **kwargs: None,
    },
    'framework.celery_tasks.handlers._enqueue_task': {
        'mark': 'enable_enqueue_task',
        'replacement': lambda *args, **kwargs: None,
    },
    'osf.models.base.BaseModel.full_clean': {
        'mark': 'enable_implicit_clean',
        'replacement': lambda *args, **kwargs: None,
    },
    'osf.models.base._check_blacklist': {
        'mark': 'enable_blacklist_check',
        'replacement': lambda *args, **kwargs: False,
    },
    'website.search.search.search_engine': {
        'mark': 'enable_search',
        'replacement': mock.MagicMock()
    },
    'website.search.elastic_search': {
        'mark': 'enable_search',
        'replacement': mock.MagicMock()
    }
}

@pytest.fixture(autouse=True, scope='session')
def _test_speedups():
    mocks = {}

    for target, config in _MOCKS.items():
        mocks[target] = mock.patch(target, config['replacement'])
        mocks[target].start()

    yield mocks

    for patcher in mocks.values():
        patcher.stop()


@pytest.fixture(autouse=True)
def _test_speedups_disable(request, settings, _test_speedups):
    patchers = []
    for target, config in _MOCKS.items():
        if not request.node.get_marker(config['mark']):
            continue
        patchers.append(_test_speedups[target])
        patchers[-1].stop()

    yield

    for patcher in patchers:
        patcher.start()
