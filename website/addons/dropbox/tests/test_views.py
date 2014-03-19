# -*- coding: utf-8 -*-
"""Views tests for the Dropbox addon."""

from nose.tools import *  # PEP8 asserts
import mock

from werkzeug import FileStorage
from webtest_plus import TestApp
from webtest import Upload

from website.util import api_url_for
from tests.base import DbTestCase, URLLookup
from tests.factories import AuthUserFactory

from website.addons.dropbox.tests.utils import DropboxAddonTestCase, app, mock_responses

lookup = URLLookup(app)


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


class TestCRUDViews(DropboxAddonTestCase):

    @mock.patch('website.addons.dropbox.views.crud.DropboxClient.put_file')
    def test_upload_file_to_folder(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('myfile.rst', b'baz','text/x-rst')}
        url = lookup('api', 'dropbox_upload', pid=self.project._primary_key,
            path='foo')
        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        mock_put_file.assert_called_once
        first_argument = mock_put_file.call_args[0][0]
        second_arg = mock_put_file.call_args[0][1]
        assert_equal(first_argument, '{0}/{1}'.format('foo', 'myfile.rst'))
        assert_true(isinstance(second_arg, FileStorage))

    @mock.patch('website.addons.dropbox.views.crud.DropboxClient.put_file')
    def test_upload_file_to_root(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('rootfile.rst', b'baz','text/x-rst')}
        url = lookup('api', 'dropbox_upload', pid=self.project._primary_key)
        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        mock_put_file.assert_called_once
        first_argument = mock_put_file.call_args[0][0]
        assert_equal(first_argument, '/rootfile.rst')
