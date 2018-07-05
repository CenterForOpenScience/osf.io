import pytest

from website.app import init_app
from framework.flask import rm_handlers
from framework.django.handlers import handlers as django_handlers


@pytest.fixture(autouse=True, scope='session')
def app():
    try:
        test_app = init_app(routes=True, set_backends=False)
    except AssertionError:  # Routes have already been set up
        test_app = init_app(routes=False, set_backends=False)

    rm_handlers(test_app, django_handlers)

    test_app.testing = True
    return test_app

