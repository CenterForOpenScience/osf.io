# -*- coding: utf-8 -*-
"""Views tests for the OneDrive addon."""
import os
import unittest
from nose.tools import *  # noqa (PEP8 asserts)
import mock
import httplib

from framework.auth import Auth
from website.util import api_url_for, web_url_for

from urllib3.exceptions import MaxRetryError

from tests.base import OsfTestCase, assert_is_redirect
from tests.factories import AuthUserFactory, ProjectFactory

from website.addons.onedrive.tests.utils import (
    OneDriveAddonTestCase, mock_responses, MockOneDrive, patch_client
)

from website.addons.onedrive import utils

mock_client = MockOneDrive()


class TestAuthViews(OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.user = AuthUserFactory()
        # Log user in
        self.app.authenticate(*self.user.auth)

#      def test_onedrive_oauth_start(self):
#          url = api_url_for('onedrive_oauth_start_user')
#          res = self.app.get(url)
#          assert_is_redirect(res)
#          assert_in('&force_reapprove=true', res.location)

#  class TestConfigViews(OneDriveAddonTestCase):

#      def test_onedrive_config_put(self):
#          url = self.project.api_url_for('onedrive_config_put')
#          # Can set folder through API call
#          res = self.app.put_json(url, {'selected': {'path': 'My test folder',
#              'name': 'OneDrive/My test folder'}},
#              auth=self.user.auth)
#          assert_equal(res.status_code, 200)
#          self.node_settings.reload()
#          self.project.reload()
#
#          # Folder was set
#          assert_equal(self.node_settings.folder, 'My test folder')
#          # A log event was created
#          last_log = self.project.logs[-1]
#          assert_equal(last_log.action, 'onedrive_folder_selected')
#          params = last_log.params
#          assert_equal(params['folder'], 'My test folder')
#
#      def test_onedrive_deauthorize(self):
#          url = self.project.api_url_for('onedrive_deauthorize')
#          saved_folder = self.node_settings.folder
#          self.app.delete(url, auth=self.user.auth)
#          self.project.reload()
#          self.node_settings.reload()
#
#          assert_false(self.node_settings.has_auth)
#          assert_is(self.node_settings.user_settings, None)
#          assert_is(self.node_settings.folder, None)
#
#          # A log event was saved
#          last_log = self.project.logs[-1]
#          assert_equal(last_log.action, 'onedrive_node_deauthorized')
#          log_params = last_log.params
#          assert_equal(log_params['node'], self.project._primary_key)
#          assert_equal(log_params['folder'], saved_folder)
#
#      def test_onedrive_get_share_emails(self):
#          # project has some contributors
#          contrib = AuthUserFactory()
#          self.project.add_contributor(contrib, auth=Auth(self.user))
#          self.project.save()
#          url = self.project.api_url_for('onedrive_get_share_emails')
#          res = self.app.get(url, auth=self.user.auth)
#          result = res.json['result']
#          assert_equal(result['emails'], [u.username for u in self.project.contributors
#                                          if u != self.user])
#          assert_equal(result['url'], utils.get_share_folder_uri(self.node_settings.folder))

#      def test_onedrive_get_share_emails_returns_error_if_not_authorizer(self):
#          contrib = AuthUserFactory()
#          contrib.add_addon('onedrive')
#          contrib.save()
#          self.project.add_contributor(contrib, auth=Auth(self.user))
#          self.project.save()
#          url = self.project.api_url_for('onedrive_get_share_emails')
#          # Non-authorizing contributor sends request
#          res = self.app.get(url, auth=contrib.auth, expect_errors=True)
#          assert_equal(res.status_code, httplib.FORBIDDEN)

#      def test_onedrive_get_share_emails_requires_user_addon(self):
#          # Node doesn't have auth
#          self.node_settings.user_settings = None
#          self.node_settings.save()
#          url = self.project.api_url_for('onedrive_get_share_emails')
#          # Non-authorizing contributor sends request
#          res = self.app.get(url, auth=self.user.auth, expect_errors=True)
#          assert_equal(res.status_code, httplib.BAD_REQUEST)


#  class TestFilebrowserViews(OneDriveAddonTestCase):

#      def test_onedrive_hgrid_data_contents(self):
#          with patch_client('website.addons.onedrive.views.hgrid.get_node_client'):
#              url = self.project.api_url_for(
#                  'onedrive_hgrid_data_contents',
#                  path=self.node_settings.folder,
#              )
#              res = self.app.get(url, auth=self.user.auth)
#              contents = [x for x in mock_client.metadata('', list=True)['contents'] if x['is_dir']]
#              assert_equal(len(res.json), len(contents))
#              first = res.json[0]
#              assert_in('kind', first)
#              assert_equal(first['path'], contents[0]['path'])
#
#      def test_onedrive_hgrid_data_contents_if_folder_is_none_and_folders_only(self):
#          with patch_client('website.addons.onedrive.views.hgrid.get_node_client'):
#              self.node_settings.folder = None
#              self.node_settings.save()
#              url = self.project.api_url_for('onedrive_hgrid_data_contents', foldersOnly=True)
#              res = self.app.get(url, auth=self.user.auth)
#              contents = mock_client.metadata('', list=True)['contents']
#              expected = [each for each in contents if each['is_dir']]
#              assert_equal(len(res.json), len(expected))
#
#      def test_onedrive_hgrid_data_contents_folders_only(self):
#          with patch_client('website.addons.onedrive.views.hgrid.get_node_client'):
#              url = self.project.api_url_for('onedrive_hgrid_data_contents', foldersOnly=True)
#              res = self.app.get(url, auth=self.user.auth)
#              contents = mock_client.metadata('', list=True)['contents']
#              expected = [each for each in contents if each['is_dir']]
#              assert_equal(len(res.json), len(expected))

#      @mock.patch('website.addons.onedrive.client.OneDriveClient.metadata')
#      def test_onedrive_hgrid_data_contents_include_root(self, mock_metadata):
#          with patch_client('website.addons.onedrive.views.hgrid.get_node_client'):
#              url = self.project.api_url_for('onedrive_hgrid_data_contents', root=1)
#
#              res = self.app.get(url, auth=self.user.auth)
#              contents = mock_client.metadata('', list=True)['contents']
#              assert_equal(len(res.json), 1)
#              assert_not_equal(len(res.json), len(contents))
#              first_elem = res.json[0]
#              assert_equal(first_elem['path'], '/')


class TestRestrictions(OneDriveAddonTestCase):

    def setUp(self):
        super(OneDriveAddonTestCase, self).setUp()

        # Nasty contributor who will try to access folders that he shouldn't have
        # access to
        self.contrib = AuthUserFactory()
        self.project.add_contributor(self.contrib, auth=Auth(self.user))
        self.project.save()

        # Set shared folder
        self.node_settings.folder = 'foo bar/bar'
        self.node_settings.save()

#      def test_restricted_config_contrib_no_addon(self):
#          url = self.project.api_url_for('onedrive_config_put')
#          res = self.app.put_json(url, {'selected': {'path': 'foo'}},
#              auth=self.contrib.auth, expect_errors=True)
#          assert_equal(res.status_code, httplib.BAD_REQUEST)

#      def test_restricted_config_contrib_not_owner(self):
#          # Contributor has onedrive auth, but is not the node authorizer
#          self.contrib.add_addon('onedrive')
#          self.contrib.save()
#
#          url = self.project.api_url_for('onedrive_config_put')
#          res = self.app.put_json(url, {'selected': {'path': 'foo'}},
#              auth=self.contrib.auth, expect_errors=True)
#          assert_equal(res.status_code, httplib.FORBIDDEN)
