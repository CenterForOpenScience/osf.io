# -*- coding: utf-8 -*-
"""Views tests for the Dropbox addon."""
import os
from nose.tools import *  # PEP8 asserts
import mock

from werkzeug import FileStorage
from webtest_plus import TestApp
from webtest import Upload

from website.util import api_url_for
from website.project.model import NodeLog
from tests.base import DbTestCase, URLLookup, assert_is_redirect
from tests.factories import AuthUserFactory

from website.addons.dropbox.tests.utils import (
    DropboxAddonTestCase, app, mock_responses, MockDropbox, patch_client
)
from website.addons.dropbox.views.config import serialize_folder, serialize_settings


lookup = URLLookup(app)
mock_client = MockDropbox()


class TestAuthViews(DbTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_dropbox_oauth_start(self):
        url = lookup('api', 'dropbox_oauth_start__user')
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
        url = lookup('api', 'dropbox_oauth_delete_user')
        res = self.app.delete(url)
        settings.reload()
        assert_false(settings.has_auth)

class TestConfigViews(DropboxAddonTestCase):

    def test_dropbox_user_config_get_has_auth_info(self):
        url = lookup('api', 'dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_equal(result['userHasAuth'], self.user_settings.has_auth)

    def test_dropbox_user_config_get_returns_correct_urls(self):
        url = lookup('api', 'dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSONified URLs result
        urls = res.json['result']['urls']
        assert_equal(urls['delete'], lookup('api', 'dropbox_oauth_delete_user'))
        assert_equal(urls['create'], lookup('api', 'dropbox_oauth_start__user'))


    def test_serialize_settings_helper_returns_correct_urls(self):
        with self.app.app.test_request_context():
            result = serialize_settings(self.node_settings, self.user, client=mock_client)
            urls = result['urls']

            assert_equal(urls['config'], self.project.api_url_for('dropbox_config_put'))
            assert_equal(urls['deauthorize'], self.project.api_url_for('dropbox_deauthorize'))
            assert_equal(urls['auth'], self.project.api_url_for('dropbox_oauth_start'))
            assert_equal(urls['importAuth'], self.project.api_url_for('dropbox_import_user_auth'))
            assert_equal(urls['files'], self.project.web_url_for('collect_file_trees__page'))

    def test_serialize_settings_helper_returns_correct_auth_info(self):
        # Need request context because url_for is used by serialize_settings
        with self.app.app.test_request_context():
            result = serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_equal(result['userHasAuth'], self.user_settings.has_auth)

    def test_serialize_settings_helper_returns_correct_folder_info(self):
        # Need request context because url_for is used by serialize_settings
        with self.app.app.test_request_context():
            result = serialize_settings(self.node_settings, self.user, client=mock_client)
        folder = result['folder']
        assert_equal(folder['name'], 'Dropbox' + self.node_settings.folder)
        assert_equal(folder['path'], self.node_settings.folder)

    def test_dropbox_config_get(self):
        with patch_client('website.addons.dropbox.views.config.get_node_addon_client'):
            self.user_settings.account_info['display_name'] = 'Foo bar'
            self.user_settings.save()

            url = lookup('api', 'dropbox_config_get', pid=self.project._primary_key)

            res = self.app.get(url, auth=self.user.auth)
            assert_equal(res.status_code, 200)
            result = res.json['result']
            # The expected folders are the simplified
            #  serialized versions of the folder metadata, including the root
            expected_folders = [{'path': '', 'name': '/ (Full Dropbox)'}] + \
                [serialize_folder(each)
                for each in mock_responses['metadata_list']['contents']
                if each['is_dir']]
            assert_equal(result['folders'], expected_folders)
            assert_equal(result['ownerName'],
                self.node_settings.user_settings.account_info['display_name'])

            assert_equal(result['urls']['config'],
                lookup('api', 'dropbox_config_put', pid=self.project._primary_key))

    def test_dropbox_config_put(self):
        url = lookup('api', 'dropbox_config_put', pid=self.project._primary_key)
        # Can set folder through API call
        res = self.app.put_json(url, {'selected': {'path': 'My test folder',
            'name': 'Dropbox/My test folder'}},
            auth=self.user.auth)
        assert_equal(res.status_code, 200)
        self.node_settings.reload()
        self.project.reload()

        # Folder was set
        assert_equal(self.node_settings.folder, 'My test folder')
        # A log event was created
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dropbox_folder_selected')
        params = last_log.params
        assert_equal(params['folder'], 'My test folder')

    def test_dropbox_deauthorize(self):
        url = lookup('api', 'dropbox_deauthorize', pid=self.project._primary_key)
        saved_folder = self.node_settings.folder
        self.app.delete(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()

        assert_false(self.node_settings.has_auth)
        assert_is(self.node_settings.user_settings, None)
        assert_is(self.node_settings.folder, None)

        # A log event was saved
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'dropbox_node_deauthorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(log_params['folder'], saved_folder)

    def test_dropbox_import_user_auth(self):
        # Node does not have user settings
        self.node_settings.user_settings = None
        self.node_settings.save()
        with patch_client('website.addons.dropbox.views.config.get_node_addon_client'):
            url = lookup('api', 'dropbox_import_user_auth', pid=self.project._primary_key)
            res = self.app.put(url, auth=self.user.auth)
            self.project.reload()
            self.node_settings.reload()
            # Need request context because serialize_settings uses url_for
            with self.app.app.test_request_context():
                expected_result = serialize_settings(self.node_settings,
                    self.user, client=mock_client)
            result = res.json['result']
            assert_equal(result, expected_result)

class TestCRUDViews(DropboxAddonTestCase):

    @mock.patch('website.addons.dropbox.client.DropboxClient.put_file')
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

    @mock.patch('website.addons.dropbox.client.DropboxClient.put_file')
    def test_upload_file_to_root(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('rootfile.rst', b'baz','text/x-rst')}
        url = lookup('api', 'dropbox_upload',
                pid=self.project._primary_key,
                path='')
        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        mock_put_file.assert_called_once
        first_argument = mock_put_file.call_args[0][0]
        node_settings = self.project.get_addon('dropbox')
        expected_path = os.path.join(node_settings.folder, 'rootfile.rst')
        assert_equal(first_argument, expected_path)

    @mock.patch('website.addons.dropbox.client.DropboxClient.file_delete')
    def test_delete_file(self, mock_file_delete):
        path = 'foo'
        res = self.app.delete(
            url=lookup('api', 'dropbox_delete_file',
                       pid=self.project._primary_key, path=path),
            auth=self.user.auth,
        )

        mock_file_delete.assert_called_once
        assert_equal(path, mock_file_delete.call_args[0][0])

    def test_download_file(self):
        assert 0, 'finish me'

    def test_render_file(self):
        assert 0, 'finish me'

    def test_dropbox_hgrid_addon_folder(self):
        assert 0, 'finish me'

    def test_dropbox_hgrid_data_contents(self):
        assert 0, 'finish me'

    def test_build_dropbox_urls(self):
        assert 0, 'finish me'

    @mock.patch('website.addons.dropbox.client.DropboxClient.put_file')
    def test_dropbox_upload_saves_a_log(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('rootfile.rst', b'baz','text/x-rst')}
        url = lookup('api', 'dropbox_upload', pid=self.project._primary_key, path='foo')
        res = self.app.post(url, payload, auth=self.user.auth)
        self.project.reload()
        last_log = self.project.logs[-1]

        assert_equal(last_log.action, 'dropbox_' + NodeLog.FILE_ADDED)
        params = last_log.params
        assert_in('project', params)
        assert_in('node', params)
        path = os.path.join('foo', 'rootfile.rst')

        assert_equal(params['path'], path)
        view_url = lookup('web', 'dropbox_view_file', path=path, pid=self.project._primary_key)
        assert_equal(params['urls']['view'], view_url)
        download_url = lookup('web', 'dropbox_download', path=path, pid=self.project._primary_key)
        assert_equal(params['urls']['download'], download_url)

    def test_dropbox_delete_file_adds_log(self):
        with patch_client('website.addons.dropbox.views.crud.get_node_addon_client'):
            path = 'foo'
            url = lookup('api', 'dropbox_delete_file', pid=self.project._primary_key,
                path=path)
            res = self.app.delete(url, auth=self.user.auth)
            self.project.reload()
            last_log = self.project.logs[-1]
            assert_equal(last_log.action, 'dropbox_' + NodeLog.FILE_REMOVED)
            params = last_log.params
            assert_in('project', params)
            assert_in('node', params)
            assert_equal(params['path'], path)

    def test_get_revisions(self):
        with patch_client('website.addons.dropbox.views.crud.get_node_addon_client'):
            path = 'foo.rst'
            url = lookup('api', 'dropbox_get_revisions', path=path,
                pid=self.project._primary_key)
            res = self.app.get(url, auth=self.user.auth)
            json_data = res.json
            result = json_data['result']
            assert_equal(len(result), len(mock_responses['revisions']))
            for each in result:
                download_link = each['download']
                assert_equal(download_link, lookup('web', 'dropbox_download',
                    pid=self.project._primary_key,
                    path=path, rev=each['rev']))
                view_link = each['view']
                assert_equal(view_link, lookup('web', 'dropbox_view_file',
                    pid=self.project._primary_key,
                    path=path, rev=each['rev']))

    def test_dropbox_view_file(self):
        url = lookup('web', 'dropbox_view_file', pid=self.project._primary_key,
            path='foo')
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, 200)
