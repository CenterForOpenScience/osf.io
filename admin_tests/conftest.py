import pytest

from website.app import init_app
from osf.migrations import ensure_default_providers


@pytest.fixture(autouse=True, scope='session')
def app_init():
    init_app(routes=False, set_backends=False)


@pytest.fixture(autouse=True)
def default_provider():
    ensure_default_providers()
