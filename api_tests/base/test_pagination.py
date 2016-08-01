# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase

from api.base.pagination import MaxSizePagination

class TestMaxPagination(ApiTestCase):
    def test_no_query_param_alters_page_size(self):
        assert MaxSizePagination.page_size_query_param is None, 'Adding variable page sizes to the paginator ' +\
            'requires tests to ensure that you can\'t request more than the class\'s maximum number of values.'
