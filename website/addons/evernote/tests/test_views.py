# -*- coding: utf-8 -*-
"""Views tests for the Evernote addon."""
import unittest
from nose.tools import *  # noqa (PEP8 asserts)
import mock
import httplib
from datetime import datetime

from framework.auth import Auth
from website.util import api_url_for
from urllib3.exceptions import MaxRetryError
# from evernote.client import EvernoteClientException
from tests.factories import AuthUserFactory

from website.addons.evernote.model import EvernoteNodeSettings
from website.addons.evernote.serializer import EvernoteSerializer
from website.addons.base import testing
from website.addons.evernote.tests.utils import (
    EvernoteAddonTestCase,
    MockEvernote,
    patch_client
)

mock_client = MockEvernote()

class TestAuthViews(EvernoteAddonTestCase, testing.views.OAuthAddonAuthViewsTestCaseMixin):

    # Need to do more? 
    # https://github.com/CenterForOpenScience/osf.io/blob/develop-backup/website/addons/owncloud/tests/test_views.py#L20
    def test_oauth_start(self):
        pass

    def setUp(self):
        self.mock_refresh = mock.patch("website.addons.evernote.model.Evernote.refresh_oauth_key")
        self.mock_refresh.return_value = True
        self.mock_refresh.start()
        super(TestAuthViews, self).setUp()

    def tearDown(self):
        self.mock_refresh.stop()
        super(TestAuthViews, self).tearDown()

    @mock.patch(
        'website.addons.box.model.BoxUserSettings.revoke_remote_oauth_access',
        mock.PropertyMock()
    )
    def test_delete_external_account(self):
        super(TestAuthViews, self).test_delete_external_account()

class TestConfigViews(EvernoteAddonTestCase, testing.views.OAuthAddonConfigViewsTestCaseMixin):

    folder = {
        'path': '/Foo',
        'id': '12234'
    }
    Serializer = EvernoteSerializer
    client = mock_client

    def setUp(self):
        self.mock_data = mock.patch.object(
            EvernoteNodeSettings,
            '_folder_data',
            return_value=(self.folder['id'], self.folder['path'])
        )
        self.mock_data.start()
        super(TestConfigViews, self).setUp()

    def tearDown(self):
        self.mock_data.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch.object(EvernoteSerializer, 'credentials_are_valid', return_value=True)
    def test_import_auth(self, *args):
        super(TestConfigViews, self).test_import_auth()

class TestFilebrowserViews(EvernoteAddonTestCase):

    def setUp(self):
        super(TestFilebrowserViews, self).setUp()
        self.user.add_addon('evernote')
        self.node_settings.external_account = self.user_settings.external_accounts[0]
        self.node_settings.save()
        self.patcher_refresh = mock.patch('website.addons.evernote.model.Evernote.refresh_oauth_key')
        self.patcher_refresh.return_value = True
        self.patcher_refresh.start()

    def tearDown(self):
        self.patcher_refresh.stop()

    def test_evernote_list_folders(self):
        with patch_client('website.addons.evernote.model.Evernote'):
            url = self.project.api_url_for('evernote_folder_list', folder_id='foo')
            print('TestFilebrowserViews.test_evernote_list_folders-->url: ', url)

            print('TestFilebrowserViews.test_evernote_list_folders-->app: ', self.app)

            res = self.app.get(url, auth=self.user.auth)
            print('TestFilebrowserViews.test_evernote_list_folders-->res.json: ', res.json)

            contents = mock_client.get_folder('', list=True)
            print('TestFilebrowserViews.test_evernote_list_folders-->contents: ', contents)

            assert_equal( res.json[0]['name'], contents['name'])

            #contents = mock_client.get_folder('', list=True)['item_collection']['entries']
            #expected = [each for each in contents if each['type']=='folder']
            #assert_equal(len(res.json), len(expected))
            #first = res.json[0]
            #assert_in('kind', first)
            #assert_equal(first['name'], contents[0]['name'])

    # @mock.patch('website.addons.evernote.model.EvernoteNodeSettings.folder_id')
    # def test_evernote_list_folders_if_folder_is_none(self, mock_folder):
    #     # If folder is set to none, no data are returned
    #     mock_folder.__get__ = mock.Mock(return_value=None)
    #     url = self.project.api_url_for('evernote_folder_list')
    #     res = self.app.get(url, auth=self.user.auth)
    #     assert_equal(len(res.json), 1)

    # def test_evernote_list_folders_if_folder_is_none_and_folders_only(self):
    #     with patch_client('website.addons.evernote.model.EvernoteClient'):
    #         self.node_settings.folder_name = None
    #         self.node_settings.save()
    #         url = api_url_for('evernote_folder_list',
    #             pid=self.project._primary_key, foldersOnly=True)
    #         res = self.app.get(url, auth=self.user.auth)
    #         contents = mock_client.get_folder('', list=True)['item_collection']['entries']
    #         expected = [each for each in contents if each['type']=='folder']
    #         assert_equal(len(res.json), len(expected))

    # def test_evernote_list_folders_folders_only(self):
    #     with patch_client('website.addons.evernote.model.EvernoteClient'):
    #         url = self.project.api_url_for('evernote_folder_list', foldersOnly=True)
    #         res = self.app.get(url, auth=self.user.auth)
    #         contents = mock_client.get_folder('', list=True)['item_collection']['entries']
    #         expected = [each for each in contents if each['type']=='folder']
    #         assert_equal(len(res.json), len(expected))

    # def test_evernote_list_folders_doesnt_include_root(self):
    #     with patch_client('website.addons.evernote.model.EvernoteClient'):
    #         url = self.project.api_url_for('evernote_folder_list', folder_id=0)
    #         res = self.app.get(url, auth=self.user.auth)
    #         contents = mock_client.get_folder('', list=True)['item_collection']['entries']
    #         expected = [each for each in contents if each['type'] == 'folder']

    #         assert_equal(len(res.json), len(expected))

    # @mock.patch('website.addons.evernote.model.EvernoteClient.get_folder')
    # def test_evernote_list_folders_deleted(self, mock_metadata):
    #     # Example metadata for a deleted folder
    #     mock_metadata.return_value = {
    #         u'bytes': 0,
    #         u'contents': [],
    #         u'hash': u'e3c62eb85bc50dfa1107b4ca8047812b',
    #         u'icon': u'folder_gray',
    #         u'is_deleted': True,
    #         u'is_dir': True,
    #         u'modified': u'Sat, 29 Mar 2014 20:11:49 +0000',
    #         u'path': u'/tests',
    #         u'rev': u'3fed844002c12fc',
    #         u'revision': 67033156,
    #         u'root': u'evernote',
    #         u'size': u'0 bytes',
    #         u'thumb_exists': False
    #     }
    #     url = self.project.api_url_for('evernote_folder_list', folder_id='foo')
    #     res = self.app.get(url, auth=self.user.auth, expect_errors=True)
    #     assert_equal(res.status_code, httplib.NOT_FOUND)

    # @mock.patch('website.addons.evernote.model.EvernoteClient.get_folder')
    # def test_evernote_list_folders_returns_error_if_invalid_path(self, mock_metadata):
    #     mock_metadata.side_effect = EvernoteClientException(status_code=404, message='File not found')
    #     url = self.project.api_url_for('evernote_folder_list', folder_id='lolwut')
    #     res = self.app.get(url, auth=self.user.auth, expect_errors=True)
    #     assert_equal(res.status_code, httplib.NOT_FOUND)

    # @mock.patch('website.addons.evernote.model.EvernoteClient.get_folder')
    # def test_evernote_list_folders_handles_max_retry_error(self, mock_metadata):
    #     mock_response = mock.Mock()
    #     url = self.project.api_url_for('evernote_folder_list', folder_id='fo')
    #     mock_metadata.side_effect = MaxRetryError(mock_response, url)
    #     res = self.app.get(url, auth=self.user.auth, expect_errors=True)
    #     assert_equal(res.status_code, httplib.BAD_REQUEST)


class TestRestrictions(EvernoteAddonTestCase):
    pass

    # def setUp(self):
    #     super(EvernoteAddonTestCase, self).setUp()

    #     # Nasty contributor who will try to access folders that he shouldn't have
    #     # access to
    #     self.contrib = AuthUserFactory()
    #     self.project.add_contributor(self.contrib, auth=Auth(self.user))
    #     self.project.save()

    #     self.user.add_addon('evernote')
    #     settings = self.user.get_addon('evernote')
    #     settings.access_token = '12345abc'
    #     settings.last_refreshed = datetime.utcnow()
    #     settings.save()

    #     self.patcher = mock.patch('website.addons.evernote.model.EvernoteNodeSettings.fetch_folder_name')
    #     self.patcher.return_value = 'foo bar/baz'
    #     self.patcher.start()

    # @mock.patch('website.addons.evernote.model.EvernoteNodeSettings.has_auth')
    # def test_restricted_hgrid_data_contents(self, mock_auth):
    #     mock_auth.__get__ = mock.Mock(return_value=False)

    #     # tries to access a parent folder
    #     url = self.project.api_url_for('evernote_folder_list',
    #         path='foo bar')
    #     res = self.app.get(url, auth=self.contrib.auth, expect_errors=True)
    #     assert_equal(res.status_code, httplib.FORBIDDEN)

    # def test_restricted_config_contrib_no_addon(self):
    #     url = api_url_for('evernote_set_config', pid=self.project._primary_key)
    #     res = self.app.put_json(url, {'selected': {'path': 'foo'}},
    #         auth=self.contrib.auth, expect_errors=True)
    #     assert_equal(res.status_code, httplib.BAD_REQUEST)

    # def test_restricted_config_contrib_not_owner(self):
    #     # Contributor has evernote auth, but is not the node authorizer
    #     self.contrib.add_addon('evernote')
    #     self.contrib.save()

    #     url = api_url_for('evernote_set_config', pid=self.project._primary_key)
    #     res = self.app.put_json(url, {'selected': {'path': 'foo'}},
    #         auth=self.contrib.auth, expect_errors=True)
    #     assert_equal(res.status_code, httplib.FORBIDDEN)