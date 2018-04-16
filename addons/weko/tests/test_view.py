# -*- coding: utf-8 -*-
import httplib as http

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, AuthUserFactory
from framework.exceptions import HTTPError

from addons.base.tests.views import (
    OAuthAddonConfigViewsTestCaseMixin
)
from addons.weko.tests.utils import WEKOAddonTestCase
from website.util import api_url_for
from addons.weko.tests.utils import ConnectionMock


class TestWEKOViews(WEKOAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    def setUp(self):
        self.mock_connect_or_error = mock.patch('addons.weko.client.connect_or_error')
        self.mock_connect_or_error.return_value = ConnectionMock()
        self.mock_connect_or_error.start()
        self.mock_connect_from_settings = mock.patch('addons.weko.client.connect_from_settings')
        self.mock_connect_from_settings.return_value = ConnectionMock()
        self.mock_connect_from_settings.start()
        super(TestWEKOViews, self).setUp()

    def tearDown(self):
        self.mock_connect_or_error.stop()
        self.mock_connect_from_settings.stop()
        super(TestWEKOViews, self).tearDown()

    def test_weko_set_index_no_settings(self):
        user = AuthUserFactory()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('weko_set_config')
        res = self.app.put_json(
            url, {'index': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_weko_set_index_no_auth(self):
        user = AuthUserFactory()
        user.add_addon('weko')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('weko_set_config')
        res = self.app.put_json(
            url, {'index': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_weko_remove_node_settings_owner(self):
        url = self.node_settings.owner.api_url_for('weko_deauthorize_node')
        ret = self.app.delete(url, auth=self.user.auth)
        result = self.Serializer().serialize_settings(node_settings=self.node_settings, current_user=self.user)
        assert_equal(result['nodeHasAuth'], False)

    def test_weko_remove_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('weko_deauthorize_node')
        ret = self.app.delete(url, auth=None, expect_errors=True)

        assert_equal(ret.status_code, 401)

    def test_weko_get_node_settings_owner(self):
        self.node_settings.set_auth(self.external_account, self.user)
        self.node_settings.index_id = 'bucket'
        self.node_settings.save()
        url = self.node_settings.owner.api_url_for('weko_get_config')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json['result']
        assert_equal(result['nodeHasAuth'], True)
        assert_equal(result['userIsOwner'], True)
        assert_equal(result['savedIndex']['id'], self.node_settings.index_id)

    def test_weko_get_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('weko_get_config')
        unauthorized = AuthUserFactory()
        ret = self.app.get(url, auth=unauthorized.auth, expect_errors=True)

        assert_equal(ret.status_code, 403)

    def test_get_config(self):
        url = self.project.api_url_for('{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        assert_in('result', res.json)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
            self.client
        )
        assert_equal(serialized, res.json['result'])

    def test_set_config(self):
        pass

    def test_folder_list(self):
        pass
