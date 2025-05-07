from osf_tests.conftest import *  # noqa

import pytest
from website import settings as website_settings

# Ensure search submodule is registered before speedup patches run
import website.search.elastic_search  # noqa: F401


@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for the test environment.
    """
    website_settings.ENABLE_PRIVATE_SEARCH = True
