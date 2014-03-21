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

from website.addons.dropbox.tests.utils import (
    DropboxAddonTestCase, app, mock_responses, MockDropbox, patch_client
)


lookup = URLLookup(app)
mock_client = MockDropbox()



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

    @mock.patch('website.addons.dropbox.model.DropboxUserSettings.update_account_info')
    @mock.patch('website.addons.dropbox.views.auth.DropboxOAuth2Flow.finish')
    def test_dropbox_oauth_finish(self, mock_finish, mock_account_info):
        mock_finish.return_value = ('mytoken123', 'mydropboxid', 'done')
        mock_account_info.return_value = {'display_name': 'Foo Bar'}
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

class TestConfigViews(DropboxAddonTestCase):

    def test_dropbox_config_get(self):
        with patch_client('website.addons.dropbox.views.config.get_client'):
            self.user_settings.account_info['display_name'] = 'Foo bar'
            self.user_settings.save()

            url = lookup('api', 'dropbox_config_get', pid=self.project._primary_key)

            res = self.app.get(url)
            assert_equal(res.status_code, 200)
            result = res.json['result']
            expected_folders = [each['path']
                for each in mock_responses['metadata_list']['contents']]
            assert_equal(result['folders'], expected_folders)
            assert_equal(result['ownerName'],
                self.node_settings.user_settings.account_info['display_name'])

            assert_equal(result['urls']['config'],
                lookup('api', 'dropbox_config_put', pid=self.project._primary_key))

    def test_dropbox_config_put(self):
        url = lookup('api', 'dropbox_config_put', pid=self.project._primary_key)
        # Can set folder through API call
        res = self.app.put_json(url, {'selected': 'My test folder'},
            auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.node_settings.reload()
        assert_equal(self.node_settings.folder, 'My test folder')


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

    @mock.patch('website.addons.dropbox.views.crud.DropboxClient', )
    def test_upload_file_to_root(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('rootfile.rst', b'baz','text/x-rst')}
        url = lookup('api', 'dropbox_upload', pid=self.project._primary_key)
        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        mock_put_file.assert_called_once
        first_argument = mock_put_file.call_args[0][0]
        assert_equal(first_argument, '/rootfile.rst')

    @mock.patch('website.addons.dropbox.views.crud.DropboxClient.file_delete')
    def test_delete_file(self, mock_file_delete):
        assert 0, 'finish me'

    @mock.patch('website.addons.dropbox.views.crud.DropboxClient.share')
    def test_download_file(self, mock_share):
        assert 0, 'finish me'

    def test_render_file(self):
        assert 0, 'finish me'

    def test_dropbox_hgrid_addon_folder(self):
        assert 0, 'finish me'

    def test_dropbox_hgrid_data_contents(self):
        assert 0, 'finish me'

    def test_build_dropbox_urls(self):
        assert 0, 'finish me'


    def test_dropbox_view_file(self):
        url = lookup('web', 'dropbox_view_file', pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)

        json = res.json
        assert 0, 'finish me'

