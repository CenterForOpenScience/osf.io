# -*- coding: utf-8 -*-
from webtest_plus import TestApp
from nose.tools import *  # PEP8 asserts

from tests.base import DbTestCase, URLLookup
from tests.factories import AuthUserFactory


from .utils import app, AppAddonTestCase

lookup = URLLookup(app)

class TestAppViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()

    def test_example(self):
        # an example test
        url = lookup('api', 'app_some_view')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
