import pytest
from osf.migrations import ensure_default_providers


@pytest.fixture(autouse=True)
def default_provider():
    ensure_default_providers()
