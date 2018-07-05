import pytest

from website.app import init_app


@pytest.fixture(autouse=True, scope='session')
def app_init():
    init_app(routes=False, set_backends=False)


@pytest.fixture(autouse=True)
def enable_implicit_clean(settings):
    settings.TEST_OPTIONS.DISABLE_IMPLICIT_FULL_CLEAN = False
