# -*- coding: utf-8 -*-


from tests.base import OsfTestCase
from tests.test_features import requires_search
from website import settings
from website.search import elastic_search
import website.search.search as search


TEST_INDEX = 'test'


@requires_search
class SearchTestCase(OsfTestCase):

    def tearDown(self):
        super(SearchTestCase, self).tearDown()
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
    def setUp(self):
        super(SearchTestCase, self).setUp()
        elastic_search.INDEX = TEST_INDEX
        settings.ELASTIC_INDEX = TEST_INDEX
        search.delete_index(elastic_search.INDEX)
        search.create_index(elastic_search.INDEX)
