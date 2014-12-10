# -*- coding: utf-8 -*-


import pytest
from . import aiopretty


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'aiopretty: mark tests to activate aiopretty'
    )


def pytest_runtest_setup(item):
    import pdb; pdb.set_trace()
    marker = item.get_marker('aiopretty')
    if marker is not None:
        aiopretty.clear()
        aiopretty.activate()


def pytest_runtest_teardown(item, nextitem):
    marker = item.get_marker('aiopretty')
    if marker is not None:
        aiopretty.deactivate()
