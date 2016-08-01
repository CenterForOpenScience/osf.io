# -*- coding: utf-8 -*-
from nose.tools import *  # noqa
import mock

import httplib as http
from tests.factories import AuthUserFactory

from framework.auth.decorators import Auth

from website.util import api_url_for
from website.addons.base.testing import views
from website.addons.owncloud.model import OwnCloudProvider
from website.addons.owncloud.serializer import OwnCloudSerializer
from website.addons.owncloud.tests.utils import (
    create_mock_owncloud, OwnCloudAddonTestCase,create_external_account
)

class TestAuthViews(OwnCloudAddonTestCase):

    def test_deauthorize(self):
        url = api_url_for('owncloud_deauthorize_node',
                          pid=self.project._primary_key)
        self.app.delete(url, auth=self.user.auth)

        self.node_settings.reload()
        assert_false(self.node_settings.folder_name)
        assert_false(self.node_settings.user_settings)

        # Log states that node was deauthorized
        self.project.reload()
        last_log = self.project.logs[-1]
        assert_equal(last_log.action, 'owncloud_node_deauthorized')
        log_params = last_log.params
        assert_equal(log_params['node'], self.project._primary_key)
        assert_equal(log_params['project'], None)

    def test_user_config_get(self):
        url = api_url_for('owncloud_user_config_get')
        new_user = AuthUserFactory.build()
        res = self.app.get(url, auth=new_user.auth)

        result = res.json.get('result')
        assert_false(result['userHasAuth'])
        assert_in('hosts', result)
        assert_in('create', result['urls'])

        # userHasAuth is true with external accounts
        new_user.external_accounts.append(create_external_account())
        new_user.save()
        res = self.app.get(url, auth=self.user.auth)

        result = res.json.get('result')
        assert_true(result['userHasAuth'])

class TestConfigViews(OwnCloudAddonTestCase, views.OAuthAddonConfigViewsTestCaseMixin):
    connection = create_mock_owncloud()
    Serializer = OwnCloudSerializer
    client = OwnCloudProvider

    @property
    def folder(self):
        return {'name':'/Documents/','path':'/Documents'}

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_ser_api = mock.patch('website.addons.owncloud.views.OwnCloudClient')
        self.mock_ser_api.return_value = create_mock_owncloud()
        self.mock_ser_api.start()
        self.set_node_settings(self.node_settings)

    def tearDown(self):
        self.mock_ser_api.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch('website.addons.owncloud.views.OwnCloudClient')
    def test_folder_list(self, mock_connection):
        #test_get_datasets
        mock_connection.return_value = self.connection

        url = api_url_for('owncloud_folder_list', pid=self.project._primary_key)
        params = {'path':'/'}
        res = self.app.get(url, params, auth=self.user.auth)
        assert_equal(len(res.json), 2)
        first = res.json[0]
        assert_equal(first['path'], '/Documents')


    def test_get_config(self):
        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('result', res.json)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
        )
        assert_equal(serialized, res.json['result'])
