import uuid

import pytest

from website import search
from website.search.drivers.disabled import SearchDisabledDriver
from website.search.drivers.elasticsearch import ElasticsearchDriver
# from website.search.drivers.legacy_elasticsearch import LegacyElasticsearchDriver


class _SearchEnabler(object):

    def __init__(self):
        self._setup = False
        self._disabled = SearchDisabledDriver(warnings=False)
        self._elasticsearch = ElasticsearchDriver([
            'http://localhost:92001',
        ], 'osf-test-{}'.format(uuid.uuid4()))

    def enable(self):
        if not self._setup:
            self._setup = True
            self._elasticsearch.setup()
        search._driver = self._elasticsearch

    def disable(self):
        search._driver = self._disabled

    def clear(self):
        # Clear out the index and make sure it's flushed to disk for the next test
        # Clearing the index is faster than dropping and recreating the entire index
        # as we'll only ever have ~10 docs at most
        self._elasticsearch._client.indices.flush()
        self._elasticsearch._client.delete_by_query(
            index=self._elasticsearch._index_prefix + '*',
            body={
                'query': {
                    'match_all': {}
                }
            },
            refresh=True,
            conflicts='proceed'
        )
        self._elasticsearch._client.indices.flush()

    def teardown(self):
        if not self._setup:
            return
        self._elasticsearch.teardown()


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
