from __future__ import print_function

import pytest

from website.app import init_app
from tests.json_api_test_app import JSONAPITestApp
from osf.migrations import ensure_default_providers


@pytest.fixture()
def app():
    return JSONAPITestApp()

# NOTE: autouse so that ADDONS_REQUESTED gets set on website.settings
@pytest.fixture(autouse=True, scope='session')
def app_init():
    init_app(routes=False, set_backends=False)

@pytest.fixture(autouse=True)
def default_provider():
    ensure_default_providers()
