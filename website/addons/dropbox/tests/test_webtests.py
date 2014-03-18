# -*- coding: utf-8 -*-
from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp
from website.app import init_app
from website.util import web_url_for, api_url_for
from website.project.model import ensure_schemas
from tests.base import DbTestCase
from tests.factories import AuthUserFactory

app = init_app(set_backends=False, routes=True)


class TestDropboxIntegration(DbTestCase):

    def setUp(self):
        ensure_schemas()
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        # User is logged in
        self.app.authenticate(*self.user.auth)

    def test_user_can_create_access_token_on_settings_page(self):
        with app.test_request_context():
            url = web_url_for('profile_settings')
        res = self.app.get(url)

        assert_not_in('Create Access Token', res)
        form = res.forms['selectAddonsForm']
        form['dropbox'] = True
        res = form.submit()
        assert_equal(res.status_code, 200)

        assert_in('Create Access Token', res)
