# -*- coding: utf-8 -*-
import hashlib
import mock
from nose.tools import *  # noqa
import pytest

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.iqbrims.tests.utils import mock_folders as sample_folder_data
from addons.iqbrims.tests.utils import IQBRIMSAddonTestCase
from osf_tests.factories import ProjectFactory
from tests.base import OsfTestCase
from addons.iqbrims.client import IQBRIMSClient, IQBRIMSFlowableClient
from addons.iqbrims.serializer import IQBRIMSSerializer
import addons.iqbrims.views as iqbrims_views
from addons.iqbrims import settings

pytestmark = pytest.mark.django_db


class TestAuthViews(IQBRIMSAddonTestCase, OAuthAddonAuthViewsTestCaseMixin, OsfTestCase):

    def setUp(self):
        super(TestAuthViews, self).setUp()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        self.mock_fetch.stop()
        super(TestAuthViews, self).tearDown()

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
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
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

class TestStatusViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestStatusViews, self).setUp()
        self.mock_about = mock.patch.object(
            IQBRIMSClient,
            'about'
        )
        self.mock_about.return_value = {'rootFolderId': '24601'}
        self.mock_about.start()
        self.mock_get_folder_info = mock.patch.object(
            IQBRIMSClient,
            'get_folder_info'
        )
        self.mock_get_folder_info.return_value = {'title': 'Test-xxxxx'}
        self.mock_get_folder_info.start()
        self.mock_rename_folder = mock.patch.object(
            IQBRIMSClient,
            'rename_folder'
        )
        self.mock_rename_folder.start()
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
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
        state = 'check'
        mock_get_management_node.return_value = mock.MagicMock(_id='fake_management_node_id')
        self.project.get_addon('iqbrims').status = state

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_in('data', res.json)
        assert_in('attributes', res.json['data'])
        assert_in('state', res.json['data']['attributes'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status(self, mock_get_management_node):
        status = {
            'state': 'fake_state',
            'other_attribute': 'fake_other_attribute'
        }
        mock_get_management_node.return_value = mock.MagicMock(_id=self.project._id)

        url = self.project.api_url_for('iqbrims_set_status')
        payload = {
            'data': {
                'attributes': status
            }
        }
        res = self.app.patch_json(url, params=payload, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
            'data': {
                'attributes': status,
                'type': 'iqbrims-status',
                'id': self.project._id
            }
        })

    @mock.patch.object(IQBRIMSFlowableClient, 'start_workflow')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_deposit(self, mock_get_management_node, mock_import_auth_from_management_node,
                                   mock_iqbrims_init_folders, mock_update_spreadsheet,
                                   mock_flowable_start_workflow):
        status = {
            'state': 'deposit',
            'labo_id': 'fake_labo_name',
            'other_attribute': 'fake_other_attribute'
        }
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        fake_management_project = ProjectFactory(creator=self.user)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_iqbrims_init_folders.return_value = fake_folder
        mock_update_spreadsheet.return_value = None
        mock_flowable_start_workflow.return_value = None

        url = self.project.api_url_for('iqbrims_set_status')
        payload = {
            'data': {
                'attributes': status
            }
        }
        res = self.app.patch_json(url, params=payload, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
            'data': {
                'attributes': status,
                'type': 'iqbrims-status',
                'id': self.project._id
            }
        })

        iqbrims = self.project.get_addon('iqbrims')
        secret = iqbrims.get_secret()
        assert_is_not_none(secret)
        assert_equal(iqbrims.folder_id, fake_folder['id'])
        assert_equal(iqbrims.folder_path, fake_folder['path'])

        assert_equal(mock_import_auth_from_management_node.call_count, 1)
        assert_items_equal(mock_import_auth_from_management_node.call_args[0], [
            self.project,
            iqbrims,
            fake_management_project
        ])

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_items_equal(mock_iqbrims_init_folders.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ])

        assert_equal(mock_update_spreadsheet.call_count, 1)
        assert_items_equal(mock_update_spreadsheet.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            payload['data']['attributes']
        ])

        assert_equal(mock_flowable_start_workflow.call_count, 1)
        assert_items_equal(mock_flowable_start_workflow.call_args[0], [
            self.project._id,
            self.project.title,
            payload['data']['attributes'],
            secret
        ])

    @mock.patch.object(IQBRIMSFlowableClient, 'start_workflow')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_check(self, mock_get_management_node, mock_import_auth_from_management_node,
                                 mock_iqbrims_init_folders, mock_update_spreadsheet,
                                 mock_flowable_start_workflow):
        status = {
            'state': 'check',
            'labo_id': 'fake_labo_name',
            'other_attribute': 'fake_other_attribute'
        }
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        fake_management_project = ProjectFactory(creator=self.user)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_iqbrims_init_folders.return_value = fake_folder
        mock_update_spreadsheet.return_value = None
        mock_flowable_start_workflow.return_value = None

        url = self.project.api_url_for('iqbrims_set_status')
        payload = {
            'data': {
                'attributes': status
            }
        }
        res = self.app.patch_json(url, params=payload, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
            'data': {
                'attributes': status,
                'type': 'iqbrims-status',
                'id': self.project._id
            }
        })

        iqbrims = self.project.get_addon('iqbrims')
        secret = iqbrims.get_secret()
        assert_is_not_none(secret)
        assert_equal(iqbrims.folder_id, fake_folder['id'])
        assert_equal(iqbrims.folder_path, fake_folder['path'])

        assert_equal(mock_import_auth_from_management_node.call_count, 1)
        assert_items_equal(mock_import_auth_from_management_node.call_args[0], [
            self.project,
            iqbrims,
            fake_management_project
        ])

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_items_equal(mock_iqbrims_init_folders.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ])

        assert_equal(mock_update_spreadsheet.call_count, 1)
        assert_items_equal(mock_update_spreadsheet.call_args[0], [
            self.project,
            fake_management_project,
            status['state'],
            payload['data']['attributes']
        ])

        assert_equal(mock_flowable_start_workflow.call_count, 1)
        assert_items_equal(mock_flowable_start_workflow.call_args[0], [
            self.project._id,
            self.project.title,
            payload['data']['attributes'],
            secret
        ])


class TestNotificationViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestNotificationViews, self).setUp()
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
        super(TestNotificationViews, self).tearDown()

    def test_unauthorized_post_notify(self):
        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()

        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post(url,
                            expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post(url, headers={'X-RDM-Token': 'invalid123'},
                            expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_has_without_mail(self, mock_get_management_node):
        mock_add_log = mock.MagicMock()
        management_project = mock.MagicMock(_id='fake_management_node_id',
                                            add_log=mock_add_log)
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        mock_add_log.assert_called_once()

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_user_has_without_mail(self, mock_get_management_node):
        mock_add_log = mock.MagicMock()
        management_project = mock.MagicMock(_id='fake_management_node_id',
                                            add_log=mock_add_log)
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['user']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        mock_add_log.assert_not_called()

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_adm_has_without_mail(self, mock_get_management_node):
        mock_add_log = mock.MagicMock()
        management_project = mock.MagicMock(_id='fake_management_node_id',
                                            add_log=mock_add_log)
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_items_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        mock_add_log.assert_called_once()
