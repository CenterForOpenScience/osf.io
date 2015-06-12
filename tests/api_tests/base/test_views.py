# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from api.base.settings.defaults import API_PREFIX

class TestApiBaseViews(ApiTestCase):

    def test_root_returns_200(self):
        res = self.app.get(API_PREFIX)
        assert_equal(res.status_code, 200)


