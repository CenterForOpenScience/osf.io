# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from tests.base import OsfTestCase
from tests.test_features import requires_search
from website import settings
from website.search import elastic_search
from website import search
from website.search.drivers import legacy_elasticsearch


TEST_INDEX = 'test'


class SearchTestCase(OsfTestCase):

    def setUp(self):
        super(SearchTestCase, self).setUp()
        search.search = LegacyElasticsearchDriver(TEST_INDEX)
        search.search.delete_index(TEST_INDEX)
        search.search.create_index(TEST_INDEX)

    def tearDown(self):
        super(SearchTestCase, self).tearDown()
        search.search.delete_index(TEST_INDEX)
