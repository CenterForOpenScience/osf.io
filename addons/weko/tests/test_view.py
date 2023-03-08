# -*- coding: utf-8 -*-
from rest_framework import status as http_status

import mock
from nose.tools import *  # noqa

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, AuthUserFactory, InstitutionFactory
from framework.exceptions import HTTPError

from addons.base.tests.views import (
    OAuthAddonConfigViewsTestCaseMixin
)
from addons.weko.tests.utils import WEKOAddonTestCase
from website.util import api_url_for
from addons.weko.tests import utils
from admin.rdm_addons.utils import get_rdm_addon_option


fake_host = 'https://weko3.test.nii.ac.jp/weko/sword/'


def mock_requests_get(url, **kwargs):
    if url == 'https://weko3.test.nii.ac.jp/weko/api/tree':
        return utils.MockResponse(utils.fake_weko_indices, 200)
    if url == 'https://weko3.test.nii.ac.jp/weko/api/index/?search_type=2&q=100':
        return utils.MockResponse(utils.fake_weko_items, 200)
    if url == 'https://weko3.test.nii.ac.jp/weko/api/records/1000':
        return utils.MockResponse(utils.fake_weko_item, 200)
    return utils.mock_response_404


class TestWEKOViews(WEKOAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    def setUp(self):
        self.mock_requests_get = mock.patch('requests.get')
        self.mock_requests_get.side_effect = mock_requests_get
        self.mock_requests_get.start()
        self.mock_find_repository = mock.patch('addons.weko.provider.find_repository')
        self.mock_find_repository.return_value = {
            'host': fake_host,
            'client_id': None,
            'client_secret': None,
            'authorize_url': None,
            'access_token_url': None,
        }
        self.mock_find_repository.start()
        super(TestWEKOViews, self).setUp()

    def tearDown(self):
        self.mock_requests_get.stop()
        self.mock_find_repository.stop()
        super(TestWEKOViews, self).tearDown()

    def test_weko_settings_rdm_addons_denied(self):
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        self.user.save()
        rdm_addon_option = get_rdm_addon_option(institution.id, self.ADDON_SHORT_NAME)
        rdm_addon_option.is_allowed = False
        rdm_addon_option.save()
        url = self.project.api_url_for('weko_oauth_connect', repoid='test')
        rv = self.app.get(
            url,
            auth=self.user.auth,
            expect_errors=True
        )
        assert_equal(rv.status_int, http_status.HTTP_403_FORBIDDEN)

    def test_weko_set_index_no_settings(self):
        user = AuthUserFactory()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('weko_set_config')
        res = self.app.put_json(
            url, {'index': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_400_BAD_REQUEST)

    def test_weko_set_index_no_auth(self):
        user = AuthUserFactory()
        user.add_addon('weko')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('weko_set_config')
        res = self.app.put_json(
            url, {'index': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http_status.HTTP_403_FORBIDDEN)

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
        assert_equal(res.status_code, http_status.HTTP_200_OK)
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
