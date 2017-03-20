import logging

import pytest
from faker import Factory

from django.db import connections, transaction
from django.db.models.signals import post_save
from django.apps import apps
from framework.django.handlers import handlers as django_handlers
from framework.flask import rm_handlers
from website import settings
from website.app import init_app, patch_models
from website.project.signals import contributor_added
from website.project.views.contributor import notify_added_contributor

# Silence some 3rd-party logging and some "loud" internal loggers
SILENT_LOGGERS = [
    'api.caching.tasks',
    'factory.generate',
    'factory.containers',
    'framework.analytics',
    'framework.auth.core',
    'framework.celery_tasks.signals',
    'website.app',
    'website.mails',
    'website.notifications.listeners',
    'website.search.elastic_search',
    'website.search_migration.migrate',
    'website.util.paths',
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

@pytest.fixture()
def transactional_db_serializer(django_db_blocker, request):
    # Django's/Pytest Django's handling of this is unrealistic when testing granular transactions.
    # The database is wiped of initial data and never repopulated so we have to do
    # all of it ourselves - h/t @chrisseto
    django_db_blocker.unblock()
    request.addfinalizer(django_db_blocker.restore)

    from django.test import TransactionTestCase
    test_case = TransactionTestCase(methodName='__init__')
    test_case._pre_setup()

    # Dump all initial data into a string :+1:
    for connection in connections.all():
        if connection.settings_dict['TEST']['MIRROR']:
            continue
        if not hasattr(connection, '_test_serialized_contents'):
            connection._test_serialized_contents = connection.creation.serialize_db_to_string()

    yield None

    test_case.serialized_rollback = True
    test_case._post_teardown()

    # Disconnect post save listeners because they screw up deserialization
    receivers, post_save.receivers = post_save.receivers, []

    if test_case.available_apps is not None:
        apps.unset_available_apps()

    for connection in connections.all():
        if connection.settings_dict['TEST']['MIRROR']:
            connection.close()
            continue
        # Everything has to be in a single transaction to avoid violating key constraints
        # It also makes it run significantly faster
        with transaction.atomic():
            connection.creation.deserialize_db_from_string(connection._test_serialized_contents)

    if test_case.available_apps is not None:
        apps.set_available_apps(test_case.available_apps)

    post_save.receivers = receivers
