# -*- coding: utf-8 -*-
"""Views tests for the Dropbox addon."""

from nose.tools import *  # PEP8 asserts
from webtest_plus import TestApp
import mock

import website
from website.util import api_url_for
from tests.base import DbTestCase
from tests.factories import AuthUserFactory

app = website.app.init_app(
    routes=True, set_backends=False, settings_module='website.settings'
)


def assert_is_redirect(response, msg='Response is a redirect'):
    assert_true(300 <= response.status_code < 400, msg)


class TestAuthViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_dropbox_oauth_start(self):
        with app.test_request_context():
            url = api_url_for('dropbox_oauth_start__user')
        res = self.app.get(url)
        assert_is_redirect(res)

    @mock.patch('website.addons.dropbox.views.auth.DropboxOAuth2Flow.finish')
    def test_dropbox_oauth_finish(self, mock_finish):
        mock_finish.return_value = ('mytoken123', 'mydropboxid', 'done')
        with app.test_request_context():
            url = api_url_for('dropbox_oauth_finish')
        res = self.app.get(url)
        assert_is_redirect(res)

    @mock.patch('website.addons.dropbox.client.DropboxClient.disable_access_token')
    def test_dropbox_oauth_delete_user(self, mock_disable_access_token):
        self.user.add_addon('dropbox')
        settings = self.user.get_addon('dropbox')
        settings.access_token = '12345abc'
        settings.save()
        assert_true(settings.has_auth)
        self.user.save()
        with app.test_request_context():
            url = api_url_for('dropbox_oauth_delete_user')

        res = self.app.delete(url)
        settings.reload()
        assert_false(settings.has_auth)
