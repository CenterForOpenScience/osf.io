from tests.mocking import aiopretty


def pytest_configure(config):
    config.addinivalue_line(
        'markers',
        'aiopretty: mark tests to activate aiopretty'
    )


def pytest_runtest_setup(item):
    marker = item.get_marker('aiopretty')
    if marker is not None:
        aiopretty.clear()
        aiopretty.activate()


def pytest_runtest_teardown(item, nextitem):
    marker = item.get_marker('aiopretty')
    if marker is not None:
        aiopretty.deactivate()
