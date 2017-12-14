import pytest

from website.app import init_app

@pytest.fixture(autouse=True, scope='session')
def app_init():
    init_app(routes=False, set_backends=False)
