import pytest

from website.app import init_app
from tests.json_api_test_app import JSONAPITestApp


@pytest.fixture()
def app():
    return JSONAPITestApp()

# NOTE: autouse so that ADDONS_REQUESTED gets set on website.settings
@pytest.fixture(autouse=True, scope='session')
def app_init():
    init_app(routes=False, set_backends=False)
