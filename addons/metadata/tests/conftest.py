from osf_tests.conftest import *  # noqa

import pytest
from website import settings as website_settings


@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for the test environment.
    """
    website_settings.ENABLE_PRIVATE_SEARCH = True
