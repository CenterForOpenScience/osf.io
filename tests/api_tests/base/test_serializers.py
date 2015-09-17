# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCasee
from tests import factories

from api.base.settings.defaults import API_BASE

class TestApiBaseSerializers(ApiTestCase):

    def setUp(self):
        super(TestApiBaseSerializers, self).setUp()

        self.node = ProjectFacti

    def test_counts_not_included_in_related_fields_by_default(self):

        self.app.get(
        pass

    def test_counts_included_in_related_fields_with_related_counts_query_param(self):
        pass

    def test_related_counts_query_param_false(self):
        pass

