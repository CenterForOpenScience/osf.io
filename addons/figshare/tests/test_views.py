#!/usr/bin/env python
# encoding: utf-8

from rest_framework import status as http_status
import mock
from nose.tools import assert_equal
import pytest

from addons.base.tests.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from addons.figshare.tests.utils import FigshareAddonTestCase
from tests.base import OsfTestCase
from addons.figshare.client import FigshareClient

pytestmark = pytest.mark.django_db

class TestAuthViews(FigshareAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):
    pass

class TestConfigViews(FigshareAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):

    ## Overrides

    @mock.patch.object(FigshareClient, 'get_folders')
    @mock.patch.object(FigshareClient, 'get_linked_folder_info')
    def test_folder_list(self, mock_about, mock_folders):
        mock_folders.return_value = [{'path': 'fileset', 'name': 'Memes', 'id': '009001'}]
        mock_about.return_value = {'path': 'fileset', 'name': 'Memes', 'id': '009001'}
        super(TestConfigViews, self).test_folder_list()

    @mock.patch.object(FigshareClient, 'get_linked_folder_info')
    def test_set_config(self, mock_about):
        # Changed from super for mocking and log action name
        mock_about.return_value = {'path': 'fileset', 'name': 'Memes', 'id': '009001'}
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'selected': self.folder
        }, auth=self.user.auth)
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        self.project.reload()
        assert_equal(
            self.project.logs.latest().action,
            '{0}_folder_selected'.format(self.ADDON_SHORT_NAME)
        )
        assert_equal(
            self.project.logs.latest().params['folder'],
            self.folder['path']
        )
        assert_equal(res.json['result']['folder']['path'], self.folder['path'])

    @mock.patch.object(FigshareClient, 'userinfo')
    def test_get_config(self, mock_about):
        super(TestConfigViews, self).test_get_config()
