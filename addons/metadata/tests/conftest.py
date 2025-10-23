from osf_tests.conftest import *  # noqa

import pytest
from website import settings as website_settings

# Ensure search submodule is registered before speedup patches run
import website.search.elastic_search  # noqa: F401


@pytest.fixture(autouse=True)
def override_settings():
    """Override settings for the test environment.
    """
    # First call the parent override_settings to ensure Celery is configured
    from framework.celery_tasks import app as celery_app
    celery_app.conf.update({
        'task_always_eager': True,
        'task_eager_propagates': True,
    })

    # Then set metadata-specific settings
    website_settings.ENABLE_PRIVATE_SEARCH = True
