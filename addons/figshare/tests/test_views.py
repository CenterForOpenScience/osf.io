#!/usr/bin/env python3

from rest_framework import status as http_status
from unittest import mock
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
        super().test_folder_list()

    @mock.patch.object(FigshareClient, 'get_linked_folder_info')
    def test_set_config(self, mock_about):
        # Changed from super for mocking and log action name
        mock_about.return_value = {'path': 'fileset', 'name': 'Memes', 'id': '009001'}
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for(f'{self.ADDON_SHORT_NAME}_set_config')
        res = self.app.put(url, json={
            'selected': self.folder
        }, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        self.project.reload()
        assert self.project.logs.latest().action == f'{self.ADDON_SHORT_NAME}_folder_selected'
        assert self.project.logs.latest().params['folder'] == self.folder['path']
        assert res.json['result']['folder']['path'] == self.folder['path']

    @mock.patch.object(FigshareClient, 'userinfo')
    def test_get_config(self, mock_about):
        super().test_get_config()
