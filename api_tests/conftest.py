# -*- coding: utf-8 -*-
import pytest

# Enable database access for all tests
def pytest_collection_modifyitems(items):
    for item in items:
        item.add_marker(pytest.mark.django_db)
