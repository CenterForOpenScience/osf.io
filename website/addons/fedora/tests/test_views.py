# -*- coding: utf-8 -*-
from nose.tools import assert_in, assert_equal
import mock

import httplib as http

from website.addons.base.testing.views import OAuthAddonAuthViewsTestCaseMixin
from website.addons.base.testing import views
from website.addons.fedora.model import FedoraProvider
from website.addons.fedora.serializer import FedoraSerializer
from website.addons.fedora.tests.utils import (FedoraAddonTestCase)


class TestAuthViews(OAuthAddonAuthViewsTestCaseMixin, FedoraAddonTestCase):

    @property
    def Provider(self):
        return FedoraProvider

    def test_oauth_start(self):
        pass

    def test_oauth_finish(self):
        pass


class TestConfigViews(FedoraAddonTestCase, views.OAuthAddonConfigViewsTestCaseMixin):
    Serializer = FedoraSerializer
    client = FedoraProvider

    @property
    def folder(self):
        return {'name': '/Documents/', 'path': '/Documents/'}

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.set_node_settings(self.node_settings)

    def tearDown(self):
        super(TestConfigViews, self).tearDown()

    @mock.patch('website.addons.fedora.model.AddonFedoraNodeSettings.get_folders')
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
