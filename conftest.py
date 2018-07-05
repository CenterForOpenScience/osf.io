import pytest

from website import search


class _SearchEnabler(object):

    def __init__(self):
        self._setup = False
        self._test_driver = search.build_driver('test')
        self._disabled_driver = search.build_driver('test-disabled')

    def enable(self):
        if not self._setup:
            self._setup = True
            self._test_driver.setup()
        search._set_driver(self._test_driver)

    def disable(self):
        search._set_driver(self._disabled_driver)

    def clear(self):
        # Clear out the index and make sure it's flushed to disk for the next test
        # Clearing the index is faster than dropping and recreating the entire index
        # as we'll only ever have ~10 docs at most
        self._test_driver._client.indices.flush()
        self._test_driver._client.delete_by_query(
            index=self._test_driver._index_prefix + '*',
            body={
                'query': {
                    'match_all': {}
                }
            },
            refresh=True,
            conflicts='proceed'
        )
        self._test_driver._client.indices.flush()

    def teardown(self):
        if not self._setup:
            return
        self._test_driver.teardown()


@pytest.fixture(scope='session')
def _searchenabler():
    enabler = _SearchEnabler()
    enabler.disable()
    yield enabler
    enabler.teardown()


@pytest.fixture(autouse=True)
def _search(request, _searchenabler):
    if not request.node.get_marker('enable_search'):
        yield
    else:
        _searchenabler.enable()
        yield
        _searchenabler.clear()
        _searchenabler.disable()
