# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa
import pytest

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.iqbrims.tests.utils import mock_folders as sample_folder_data
from addons.iqbrims.tests.utils import IQBRIMSAddonTestCase
from tests.base import OsfTestCase
from addons.iqbrims.client import IQBRIMSClient
from addons.iqbrims.serializer import IQBRIMSSerializer
import addons.iqbrims.views as iqbrims_views
from addons.iqbrims import settings

pytestmark = pytest.mark.django_db


class TestAuthViews(IQBRIMSAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):
    pass

class TestConfigViews(IQBRIMSAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = {
        'path': 'Drive/Camera Uploads',
        'id': '1234567890'
    }
    Serializer = IQBRIMSSerializer
    client = IQBRIMSClient

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_about = mock.patch.object(
            IQBRIMSClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_fetch.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch.object(IQBRIMSClient, 'folders')
    def test_folder_list_not_root(self, mock_drive_client_folders):
        mock_drive_client_folders.return_value = sample_folder_data['items']
        folderId = '12345'
        self.node_settings.set_auth(external_account=self.external_account, user=self.user)
        self.node_settings.save()

        url = self.project.api_url_for('iqbrims_folder_list', folder_id=folderId)
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), len(sample_folder_data['items']))

    @mock.patch.object(IQBRIMSClient, 'about')
    def test_folder_list(self, mock_about):
        mock_about.return_value = {'rootFolderId': '24601'}
        super(TestConfigViews, self).test_folder_list()

class TestStatusViews(IQBRIMSAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    folder = {
        'path': 'Drive/Camera Uploads',
        'id': '1234567890'
    }
    Serializer = IQBRIMSSerializer
    client = IQBRIMSClient

    def setUp(self):
        super(TestStatusViews, self).setUp()
        self.mock_about = mock.patch.object(
            IQBRIMSClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_fetch.stop()
        super(TestStatusViews, self).tearDown()

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status(self, mock_get_management_node):
        mock_get_management_node.return_value = mock.MagicMock(_id='fake_management_node_id')

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json.keys(), ['data'])
        assert_items_equal(res.json['data'].keys(), ['id', 'type', 'attributes'])
        assert_equal(res.json['data']['id'], self.project._id)
        assert_equal(res.json['data']['type'], 'iqbrims-status')
        assert_items_equal(res.json['data']['attributes'].keys(), ['state', 'labo_list', 'review_folders', 'is_admin'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')
        assert_equal(len(res.json['data']['attributes']['labo_list']), len(settings.LABO_LIST))
        assert_equal(res.json['data']['attributes']['review_folders'], iqbrims_views.REVIEW_FOLDERS)
        assert_equal(res.json['data']['attributes']['is_admin'], False)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status_with_admin(self, mock_get_management_node):
        mock_get_management_node.return_value = mock.MagicMock(_id=self.project._id)

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json.keys(), ['data'])
        assert_items_equal(res.json['data'].keys(), ['id', 'type', 'attributes'])
        assert_equal(res.json['data']['id'], self.project._id)
        assert_equal(res.json['data']['type'], 'iqbrims-status')
        assert_items_equal(res.json['data']['attributes'].keys(), ['state', 'labo_list', 'review_folders', 'is_admin',
                                                                   'task_url'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')
        assert_equal(len(res.json['data']['attributes']['labo_list']), len(settings.LABO_LIST))
        assert_equal(res.json['data']['attributes']['review_folders'], iqbrims_views.REVIEW_FOLDERS)
        assert_equal(res.json['data']['attributes']['is_admin'], True)
        assert_equal(res.json['data']['attributes']['task_url'], settings.FLOWABLE_TASK_URL)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status_with_other_state(self, mock_get_management_node):
        mock_get_management_node.return_value = mock.MagicMock(_id='fake_management_node_id')
        state = 'check'
        self.project.get_addon('iqbrims').status = state

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_in('data', res.json)
        assert_in('attributes', res.json['data'])
        assert_in('state', res.json['data']['attributes'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')
