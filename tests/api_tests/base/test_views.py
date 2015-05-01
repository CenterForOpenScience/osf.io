# -*- coding: utf-8 -*-
from nose.tools import *  # flake8: noqa

from tests.base import OsfTestCase

class TestApiBaseViews(OsfTestCase):

    def test_root_returns_200(self):
        res = self.app.get('/api/v2/')
        assert_equal(res.status_code, 200)


