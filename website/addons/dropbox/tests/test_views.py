# -*- coding: utf-8 -*-
"""Views tests for the Dropbox addon."""
import os
import unittest
from nose.tools import *  # PEP8 asserts
import mock
import httplib
import datetime

from werkzeug import FileStorage
from webtest_plus import TestApp
from webtest import Upload
from framework.auth.decorators import Auth
from website.util import api_url_for, web_url_for
from website.project.model import NodeLog
from tests.base import OsfTestCase, assert_is_redirect
from tests.factories import AuthUserFactory

from website.addons.dropbox.tests.utils import (
    DropboxAddonTestCase, app, mock_responses, MockDropbox, patch_client
)
from website.addons.dropbox.views.config import serialize_settings
from website.addons.dropbox import utils

mock_client = MockDropbox()


class TestAuthViews(OsfTestCase):

    def setUp(self):
        self.app = TestApp(app)
        self.user = AuthUserFactory()
        # Log user in
        self.app.authenticate(*self.user.auth)

    def test_dropbox_oauth_start(self):
        url = api_url_for('dropbox_oauth_start_user')
        res = self.app.get(url)
        assert_is_redirect(res)

    @mock.patch('website.addons.dropbox.views.auth.DropboxOAuth2Flow.finish')
    def test_dropbox_oauth_finish(self, mock_finish):
        mock_finish.return_value = ('mytoken123', 'mydropboxid', 'done')
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
        url = api_url_for('dropbox_oauth_delete_user')
        res = self.app.delete(url)
        settings.reload()
        assert_false(settings.has_auth)


class TestConfigViews(DropboxAddonTestCase):

    def test_dropbox_user_config_get_has_auth_info(self):
        url = api_url_for('dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSON result
        result = res.json['result']
        assert_true(result['userHasAuth'])

    def test_dropbox_user_config_get_returns_correct_urls(self):
        url = api_url_for('dropbox_user_config_get')
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        # The JSONified URLs result
        urls = res.json['result']['urls']
        assert_equal(urls['delete'], api_url_for('dropbox_oauth_delete_user'))
        assert_equal(urls['create'], api_url_for('dropbox_oauth_start_user'))

    def test_serialize_settings_helper_returns_correct_urls(self):
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        urls = result['urls']

        assert_equal(urls['config'], self.project.api_url_for('dropbox_config_put'))
        assert_equal(urls['deauthorize'], self.project.api_url_for('dropbox_deauthorize'))
        assert_equal(urls['auth'], self.project.api_url_for('dropbox_oauth_start'))
        assert_equal(urls['importAuth'], self.project.api_url_for('dropbox_import_user_auth'))
        assert_equal(urls['files'], self.project.web_url_for('collect_file_trees__page'))
        assert_equal(urls['share'], utils.get_share_folder_uri(self.node_settings.folder))
        # Includes endpoint for fetching folders only
        # NOTE: Querystring params are in camelCase
        assert_equal(urls['folders'],
            self.project.api_url_for('dropbox_hgrid_data_contents', foldersOnly=1, includeRoot=1))

    def test_serialize_settings_helper_returns_correct_auth_info(self):
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        assert_equal(result['nodeHasAuth'], self.node_settings.has_auth)
        assert_true(result['userHasAuth'])
        assert_true(result['userIsOwner'])

    def test_serialize_settings_for_user_no_auth(self):
        no_addon_user = AuthUserFactory()
        result = serialize_settings(self.node_settings, no_addon_user, client=mock_client)
        assert_false(result['userIsOwner'])
        assert_false(result['userHasAuth'])


    def test_serialize_settings_helper_returns_correct_folder_info(self):
        result = serialize_settings(self.node_settings, self.user, client=mock_client)
        folder = result['folder']
        assert_equal(folder['name'], 'Dropbox' + self.node_settings.folder)
        assert_equal(folder['path'], self.node_settings.folder)

    def test_dropbox_config_get(self):
        self.user_settings.save()

        url = api_url_for('dropbox_config_get', pid=self.project._primary_key)

        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        result = res.json['result']
        assert_equal(result['ownerName'], self.user_settings.owner.fullname)

        assert_equal(result['urls']['config'],
            api_url_for('dropbox_config_put', pid=self.project._primary_key))

    def test_dropbox_config_put(self):
        url = api_url_for('dropbox_config_put', pid=self.project._primary_key)
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
        url = api_url_for('dropbox_deauthorize', pid=self.project._primary_key)
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

    def test_dropbox_import_user_auth_returns_serialized_settings(self):
        # Node does not have user settings
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('dropbox_import_user_auth', pid=self.project._primary_key)
        res = self.app.put(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()
        expected_result = serialize_settings(self.node_settings, self.user,
                                             client=mock_client)
        result = res.json['result']
        assert_equal(result, expected_result)

    def test_dropbox_import_user_auth_adds_a_log(self):
        # Node does not have user settings
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('dropbox_import_user_auth', pid=self.project._primary_key)
        self.app.put(url, auth=self.user.auth)
        self.project.reload()
        self.node_settings.reload()
        last_log = self.project.logs[-1]

        assert_equal(last_log.action, 'dropbox_node_authorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(last_log.user, self.user)

    def test_dropbox_get_share_emails(self):
        # project has some contributors
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.user))
        self.project.save()
        url = api_url_for('dropbox_get_share_emails', pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        result = res.json['result']
        assert_equal(result['emails'], [u.username for u in self.project.contributors
                                        if u != self.user])
        assert_equal(result['url'], utils.get_share_folder_uri(self.node_settings.folder))

    def test_dropbox_get_share_emails_returns_error_if_not_authorizer(self):
        contrib = AuthUserFactory()
        contrib.add_addon('dropbox')
        contrib.save()
        self.project.add_contributor(contrib, auth=Auth(self.user))
        self.project.save()
        url = api_url_for('dropbox_get_share_emails', pid=self.project._primary_key)
        # Non-authorizing contributor sends request
        res = self.app.get(url, auth=contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_dropbox_get_share_emails_requires_user_addon(self):
        # Node doesn't have auth
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = api_url_for('dropbox_get_share_emails', pid=self.project._primary_key)
        # Non-authorizing contributor sends request
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)


class TestFilebrowserViews(DropboxAddonTestCase):

    def test_dropbox_hgrid_data_contents(self):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            url = api_url_for('dropbox_hgrid_data_contents',
                path=self.node_settings.folder,
                pid=self.project._primary_key)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            assert_equal(len(res.json), len(contents))
            first = res.json[0]
            assert_in('kind', first)
            assert_equal(first['path'], contents[0]['path'])

    def test_dropbox_hgrid_data_contents_if_folder_is_none(self):
        # If folder is set to none, no data are returned
        self.node_settings.folder = None
        self.node_settings.save()
        url = api_url_for('dropbox_hgrid_data_contents', pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.json['data'], [])

    def test_dropbox_hgrid_data_contents_if_folder_is_none_and_folders_only(self):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            self.node_settings.folder = None
            self.node_settings.save()
            url = api_url_for('dropbox_hgrid_data_contents',
                pid=self.project._primary_key, foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            expected = [each for each in contents if each['is_dir']]
            assert_equal(len(res.json), len(expected))

    def test_dropbox_hgrid_data_contents_folders_only(self):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            url = api_url_for('dropbox_hgrid_data_contents',
                pid=self.project._primary_key, foldersOnly=True)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            expected = [each for each in contents if each['is_dir']]
            assert_equal(len(res.json), len(expected))

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_dropbox_hgrid_data_contents_include_root(self, mock_metadata):
        with patch_client('website.addons.dropbox.views.hgrid.get_node_client'):
            url = api_url_for('dropbox_hgrid_data_contents',
                pid=self.project._primary_key, includeRoot=1)
            res = self.app.get(url, auth=self.user.auth)
            contents = mock_client.metadata('', list=True)['contents']
            assert_equal(len(res.json), len(contents) + 1)
            first_elem = res.json[0]
            assert_equal(first_elem['path'], '/')

    @unittest.skip('finish this')
    def test_dropbox_addon_folder(self):
        assert 0, 'finish me'

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_dropbox_hgrid_data_contents_deleted(self, mock_metadata):
        # Example metadata for a deleted folder
        mock_metadata.return_value = {
            u'bytes': 0,
            u'contents': [],
            u'hash': u'e3c62eb85bc50dfa1107b4ca8047812b',
            u'icon': u'folder_gray',
            u'is_deleted': True,
            u'is_dir': True,
            u'modified': u'Sat, 29 Mar 2014 20:11:49 +0000',
            u'path': u'/tests',
            u'rev': u'3fed844002c12fc',
            u'revision': 67033156,
            u'root': u'dropbox',
            u'size': u'0 bytes',
            u'thumb_exists': False
        }
        url = self.project.api_url_for('dropbox_hgrid_data_contents')
        res = self.app.get(url, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.NOT_FOUND)


class TestRestrictions(DropboxAddonTestCase):

    def setUp(self):
        super(DropboxAddonTestCase, self).setUp()

        # Nasty contributor who will try to access folders that he shouldn't have
        # access to
        self.contrib = AuthUserFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.user))
        self.project.save()

        # Set shared folder
        self.node_settings.folder = 'foo bar/bar'
        self.node_settings.save()

    @mock.patch('website.addons.dropbox.client.DropboxClient.file_delete')
    def test_restricted_deletion(self, mock_file_delete):
        # Tries to delete a file in a parent folder of the shared folder (foo bar)
        url = api_url_for('dropbox_delete_file', 'dropbox_delete_file',
            pid=self.project._primary_key, path='foo bar/secret.txt')
        # gets 403 error
        res = self.app.delete(url=url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    @mock.patch('website.addons.dropbox.client.DropboxClient.put_file')
    def test_restricted_uploads(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        # tries to uplaod file to a parent folder of shared folder
        url = api_url_for('dropbox_upload', pid=self.project._primary_key,
            path='foo bar')
        payload = {'file': Upload('myfile.rst', b'baz', 'text/x-rst')}
        res = self.app.post(url, payload, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    @mock.patch('website.addons.dropbox.client.DropboxClient.metadata')
    def test_restricted_hgrid_data_contents(self, mock_metadata):
        mock_metadata.return_value = mock_responses['metadata_list']

        # tries to access a parent folder
        url = self.project.api_url_for('dropbox_hgrid_data_contents',
            path='foo bar')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_restricted_view_file(self):
        url = web_url_for('dropbox_view_file',
            pid=self.project._primary_key,
            path='foo bar/baz.txt')
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_restricted_get_revisions(self):
        path = 'foo bar/baz.rst'
        url = api_url_for('dropbox_get_revisions', path=path,
            pid=self.project._primary_key)
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_restricted_download(self):
        path = 'foo bar/baz.rst'
        url = web_url_for('dropbox_download', path=path, pid=self.project._primary_key)
        res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)

    def test_restricted_config_contrib_no_addon(self):
        url = api_url_for('dropbox_config_put', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.BAD_REQUEST)

    def test_restricted_config_contrib_not_owner(self):
        # Contributor has dropbox auth, but is not the node authorizer
        self.contrib.add_addon('dropbox')
        self.contrib.save()

        url = api_url_for('dropbox_config_put', pid=self.project._primary_key)
        res = self.app.put_json(url, {'selected': {'path': 'foo'}},
            auth=self.contrib.auth, expect_errors=True)
        assert_equal(res.status_code, httplib.FORBIDDEN)


class TestCRUDViews(DropboxAddonTestCase):

    @mock.patch('website.addons.dropbox.client.DropboxClient.put_file')
    def test_upload_file_to_folder(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('myfile.rst', b'baz', 'text/x-rst')}
        url = api_url_for('dropbox_upload', pid=self.project._primary_key,
            path='foo')
        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, httplib.CREATED)
        mock_put_file.assert_called_once
        first_argument = mock_put_file.call_args[0][0]
        second_arg = mock_put_file.call_args[0][1]
        assert_equal(first_argument, '{0}/{1}'.format('foo', 'myfile.rst'))
        assert_true(isinstance(second_arg, FileStorage))

    @mock.patch('website.addons.dropbox.client.DropboxClient.put_file')
    def test_upload_file_to_root(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('rootfile.rst', b'baz', 'text/x-rst')}
        url = api_url_for('dropbox_upload',
                pid=self.project._primary_key,
                path='')
        res = self.app.post(url, payload, auth=self.user.auth)
        assert_equal(res.status_code, httplib.CREATED)
        mock_put_file.assert_called_once
        first_argument = mock_put_file.call_args[0][0]
        node_settings = self.project.get_addon('dropbox')
        expected_path = os.path.join(node_settings.folder, 'rootfile.rst')
        assert_equal(first_argument, expected_path)

    @mock.patch('website.addons.dropbox.client.DropboxClient.file_delete')
    def test_delete_file(self, mock_file_delete):
        path = 'foo'
        res = self.app.delete(
            url=api_url_for('dropbox_delete_file',
                       pid=self.project._primary_key, path=path),
            auth=self.user.auth,
        )

        mock_file_delete.assert_called_once
        assert_equal(path, mock_file_delete.call_args[0][0])

    @unittest.skip('Finish this')
    def test_download_file(self):
        assert 0, 'finish me'

    @unittest.skip('Finish this')
    def test_render_file(self):
        assert 0, 'finish me'

    @unittest.skip('Finish this')
    def test_build_dropbox_urls(self):
        assert 0, 'finish me'

    @mock.patch('website.addons.dropbox.client.DropboxClient.put_file')
    def test_dropbox_upload_saves_a_log(self, mock_put_file):
        mock_put_file.return_value = mock_responses['put_file']
        payload = {'file': Upload('rootfile.rst', b'baz','text/x-rst')}
        url = api_url_for('dropbox_upload', pid=self.project._primary_key, path='foo')
        res = self.app.post(url, payload, auth=self.user.auth)
        self.project.reload()
        last_log = self.project.logs[-1]

        assert_equal(last_log.action, 'dropbox_' + NodeLog.FILE_ADDED)
        params = last_log.params
        assert_in('project', params)
        assert_in('node', params)
        path = os.path.join('foo', 'rootfile.rst')

        assert_equal(params['path'], path)
        view_url = web_url_for('dropbox_view_file', path=path, pid=self.project._primary_key)
        assert_equal(params['urls']['view'], view_url)
        download_url = web_url_for('dropbox_download', path=path, pid=self.project._primary_key)
        assert_equal(params['urls']['download'], download_url)

    def test_dropbox_delete_file_adds_log(self):
        with patch_client('website.addons.dropbox.views.crud.get_node_addon_client'):
            path = 'foo'
            url = api_url_for('dropbox_delete_file', pid=self.project._primary_key,
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
            url = api_url_for('dropbox_get_revisions', path=path,
                pid=self.project._primary_key)
            res = self.app.get(url, auth=self.user.auth)
            json_data = res.json
            result = json_data['result']
            expected = [rev for rev in mock_responses['revisions'] if not rev.get('is_deleted')]
            assert_equal(len(result), len(expected))
            for each in result:
                download_link = each['download']
                assert_equal(download_link, web_url_for('dropbox_download',
                    pid=self.project._primary_key,
                    path=path, rev=each['rev']))
                view_link = each['view']
                assert_equal(view_link, web_url_for('dropbox_view_file',
                    pid=self.project._primary_key,
                    path=path, rev=each['rev']))

    @mock.patch('website.addons.dropbox.client.DropboxClient.revisions')
    def test_get_revisions_does_not_return_deleted_revisions(self, mock_revisions):
        mock_revisions.return_value = [
            {'path': 'foo.txt', 'rev': '123'},
            {'path': 'foo.txt', 'rev': '456', 'is_deleted': True}
        ]
        url = api_url_for('dropbox_get_revisions', path='foo.txt',
            pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        res_data = res.json['result']
        # Deleted revision was excluded
        assert_equal(len(res_data), 1)

    @mock.patch('website.addons.dropbox.client.DropboxClient.revisions')
    def test_get_revisions_returns_registration_date(self, mock_revisions):
        mock_revisions.return_value = [
            {'path': 'foo.txt', 'rev': '123'},
            {'path': 'foo.txt', 'rev': '456', 'is_deleted': True}
        ]
        # Make project a registration
        self.project.is_registration = True
        self.project.registered_date = datetime.datetime.utcnow()
        self.project.save()
        url = api_url_for('dropbox_get_revisions',
            path='foo.txt',
            pid=self.project._primary_key)
        res = self.app.get(url, auth=self.user.auth)
        assert_true(res.json['registered'])
        # Compare with second precision
        assert_equal(res.json['registered'][:19],
            self.project.registered_date.isoformat()[:19])


    def test_dropbox_view_file(self):
        url = web_url_for('dropbox_view_file', pid=self.project._primary_key,
            path='foo')
        res = self.app.get(url, auth=self.user.auth).maybe_follow()
        assert_equal(res.status_code, 200)
