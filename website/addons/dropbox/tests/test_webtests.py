# -*- coding: utf-8 -*-
from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp
from website.app import init_app
from tests.base import OsfTestCase, URLLookup
from tests.factories import AuthUserFactory

app = init_app(set_backends=False, routes=True)

lookup = URLLookup(app)


class TestDropboxIntegration(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        # User is logged in
        self.app.authenticate(*self.user.auth)

    def test_cant_start_oauth_if_already_authorized(self):
        # User already has dropbox authorized
        self.user.add_addon('dropbox')
        self.user.save()
        settings = self.user.get_addon('dropbox')
        settings.access_token = 'abc123foobarbaz'
        settings.save()
        assert_true(self.user.get_addon('dropbox').has_auth)
        # Tries to start oauth again
        url = lookup('api', 'dropbox_oauth_start_user')
        res = self.app.get(url).follow()

        # Is redirected back to settings page
        assert_equal(res.request.path,
            lookup('web', 'user_addons'))
