# -*- coding: utf-8 -*-
from nose.tools import assert_in, assert_equal
import mock
import pytest

import httplib as http

from addons.base.tests.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from addons.nextcloud.models import NextcloudProvider
from tests.base import OsfTestCase
from addons.nextcloud.serializer import NextcloudSerializer
from addons.nextcloud.tests.utils import NextcloudAddonTestCase

pytestmark = pytest.mark.django_db

class TestAuthViews(OAuthAddonAuthViewsTestCaseMixin, NextcloudAddonTestCase, OsfTestCase):

    @property
    def Provider(self):
        return NextcloudProvider

    def test_oauth_start(self):
        pass

    def test_oauth_finish(self):
        pass


class TestConfigViews(NextcloudAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    Serializer = NextcloudSerializer
    client = NextcloudProvider

    @property
    def folder(self):
        return {'name': '/Documents/', 'path': '/Documents/'}

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_ser_api = mock.patch('nextcloud.Client.login')
        self.mock_ser_api.start()
        self.set_node_settings(self.node_settings)

    def tearDown(self):
        self.mock_ser_api.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch('addons.nextcloud.models.NodeSettings.get_folders')
    def test_folder_list(self, mock_connection):
        #test_get_datasets
        mock_connection.return_value = ['/Documents/', '/Pictures/', '/Videos/']

        super(TestConfigViews, self).test_folder_list()

    def test_get_config(self):
        url = self.project.api_url_for(
            '{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('result', res.json)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
        )
        assert_equal(serialized, res.json['result'])
