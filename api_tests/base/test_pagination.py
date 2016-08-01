# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase

from api.base.pagination import MaxSizePagination

class TestMaxPagination(ApiTestCase):
    def test_no_query_param_alters_page_size(self):
        assert_is_none(MaxSizePagination.page_size_query_param)
