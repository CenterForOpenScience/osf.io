# -*- coding: utf-8 -*-
import hashlib
import json
import mock
from nose.tools import *  # noqa
import pytest
import re
from urllib.parse import quote

from addons.base.tests.views import OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
from addons.iqbrims.tests.utils import mock_folders as sample_folder_data
from addons.iqbrims.tests.utils import IQBRIMSAddonTestCase
from osf.models import Comment
from osf_tests.factories import ProjectFactory
from tests.base import OsfTestCase
from addons.iqbrims.client import (
    IQBRIMSClient,
    IQBRIMSFlowableClient,
    SpreadsheetClient,
    IQBRIMSWorkflowUserSettings
)
from addons.iqbrims.serializer import IQBRIMSSerializer
import addons.iqbrims.views as iqbrims_views
from addons.iqbrims import settings
from website import mails
from addons.iqbrims.tests.utils import MockResponse

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
        self.mock_load_settings = mock.patch.object(
            IQBRIMSWorkflowUserSettings,
            'load'
        )
        self.mock_load_settings.return_value = {'settings': {}}
        self.mock_load_settings.start()
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
        self.mock_load_settings.stop()
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
        self.mock_fetch.stop()
        super(TestStatusViews, self).tearDown()

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status(self, mock_get_management_node):
        fake_management_project = ProjectFactory(creator=self.user)
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(list(res.json.keys()), ['data'])
        assert_equal(list(res.json['data'].keys()), ['id', 'type', 'attributes'])
        assert_equal(res.json['data']['id'], self.project._id)
        assert_equal(res.json['data']['type'], 'iqbrims-status')
        assert_equal(list(res.json['data']['attributes'].keys()),
                     ['state', 'labo_list', 'review_folders', 'is_admin'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')
        assert_equal(len(res.json['data']['attributes']['labo_list']), len(settings.LABO_LIST))
        assert_equal(res.json['data']['attributes']['review_folders'], iqbrims_views.REVIEW_FOLDERS)
        assert_equal(res.json['data']['attributes']['is_admin'], False)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status_with_admin(self, mock_get_management_node):
        mock_get_management_node.return_value = self.project

        url = self.project.api_url_for('iqbrims_get_status')
        res = self.app.get(url, auth=self.user.auth)

        assert_equal(res.status_code, 200)
        assert_equal(list(res.json.keys()), ['data'])
        assert_equal(list(res.json['data'].keys()), ['id', 'type', 'attributes'])
        assert_equal(res.json['data']['id'], self.project._id)
        assert_equal(res.json['data']['type'], 'iqbrims-status')
        assert_equal(list(res.json['data']['attributes'].keys()),
                     ['state', 'labo_list', 'review_folders', 'is_admin',
                      'task_url'])
        assert_equal(res.json['data']['attributes']['state'], 'initialized')
        assert_equal(len(res.json['data']['attributes']['labo_list']), len(settings.LABO_LIST))
        assert_equal(res.json['data']['attributes']['review_folders'], iqbrims_views.REVIEW_FOLDERS)
        assert_equal(res.json['data']['attributes']['is_admin'], True)
        assert_equal(res.json['data']['attributes']['task_url'], settings.FLOWABLE_TASK_URL)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_get_status_with_other_state(self, mock_get_management_node):
        state = 'check'
        fake_management_project = ProjectFactory(creator=self.user)
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project
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

    @mock.patch.object(IQBRIMSFlowableClient, '_make_request')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_deposit(self, mock_get_management_node, mock_import_auth_from_management_node,
                                   mock_iqbrims_init_folders, mock_update_spreadsheet,
                                   mock_flowable_make_request):
        status = {
            'state': 'deposit',
            'labo_id': 'fake_labo_name',
            'other_attribute': 'fake_other_attribute',
            'is_dirty': False,
            'workflow_paper_permissions': ['READ', 'WRITE', 'UPLOADABLE'],
        }
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        fake_management_project = ProjectFactory(creator=self.user)
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_client = mock.MagicMock()
        mock_iqbrims_init_folders.return_value = mock_client, fake_folder
        mock_update_spreadsheet.return_value = None
        mock_flowable_make_request.return_value = MockResponse('{"test": 1}',
                                                               200)
        mock_client.folders.return_value = [{
            'id': 'FOLDER67890',
            'title': '最終原稿・組図',
        }]

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
        assert_equal(mock_import_auth_from_management_node.call_args[0], (
            self.project,
            iqbrims,
            fake_management_project
        ))

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_equal(mock_iqbrims_init_folders.call_args[0], (
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ))

        assert_equal(mock_update_spreadsheet.call_count, 1)
        assert_equal(mock_update_spreadsheet.call_args[0], (
            self.project,
            fake_management_project,
            status['state'],
            payload['data']['attributes']
        ))

        assert_equal(mock_flowable_make_request.call_count, 1)
        name, args, kwargs = mock_flowable_make_request.mock_calls[0]
        assert_equal(args, ('POST', settings.FLOWABLE_HOST +
                                    'service/runtime/process-instances'))
        assert_equal(json.loads(kwargs['data'])['processDefinitionId'],
                     settings.FLOWABLE_RESEARCH_APP_ID)
        vars = json.loads(kwargs['data'])['variables']
        assert_equal([v for v in vars if v['name'] == 'projectId'][0], {
          'name': 'projectId',
          'type': 'string',
          'value': self.project._id
        })
        assert_equal([v for v in vars if v['name'] == 'paperFolderPattern'][0], {
          'name': 'paperFolderPattern',
          'type': 'string',
          'value': 'deposit/fake_labo_name/%-{}/'.format(self.project._id)
        })

        assert_equal(len(mock_client.grant_access_from_anyone.call_args_list), 1)
        assert_equal(mock_client.grant_access_from_anyone.call_args_list[0][0][0], 'FOLDER67890')
        assert_equal(len(mock_client.revoke_access_from_anyone.call_args_list), 0)

    @mock.patch.object(IQBRIMSFlowableClient, 'start_workflow')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_confirm(self, mock_get_management_node, mock_import_auth_from_management_node,
                                   mock_iqbrims_init_folders, mock_update_spreadsheet,
                                   mock_flowable_start_workflow):
        status = {
            'state': 'deposit',
            'labo_id': 'fake_labo_name',
            'other_attribute': 'fake_other_attribute',
            'is_dirty': True
        }
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        fake_management_project = ProjectFactory(creator=self.user)
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_client = mock.MagicMock()
        mock_iqbrims_init_folders.return_value = mock_client, fake_folder
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
        assert_equal(mock_import_auth_from_management_node.call_args[0], (
            self.project,
            iqbrims,
            fake_management_project
        ))

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_equal(mock_iqbrims_init_folders.call_args[0], (
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ))

        assert_equal(mock_update_spreadsheet.call_count, 0)

    @mock.patch.object(IQBRIMSFlowableClient, '_make_request')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_check(self, mock_get_management_node, mock_import_auth_from_management_node,
                                 mock_iqbrims_init_folders, mock_update_spreadsheet,
                                 mock_flowable_make_request):
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
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_client = mock.MagicMock()
        mock_iqbrims_init_folders.return_value = mock_client, fake_folder
        mock_update_spreadsheet.return_value = None
        mock_flowable_make_request.return_value = MockResponse('{"test": 1}',
                                                               200)

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
        assert_equal(mock_import_auth_from_management_node.call_args[0], (
            self.project,
            iqbrims,
            fake_management_project
        ))

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_equal(mock_iqbrims_init_folders.call_args[0], (
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ))

        assert_equal(mock_update_spreadsheet.call_count, 1)
        assert_equal(mock_update_spreadsheet.call_args[0], (
            self.project,
            fake_management_project,
            status['state'],
            payload['data']['attributes']
        ))

        assert_equal(mock_flowable_make_request.call_count, 1)
        name, args, kwargs = mock_flowable_make_request.mock_calls[0]
        assert_equal(args, ('POST', settings.FLOWABLE_HOST +
                                    'service/runtime/process-instances'))
        assert_equal(json.loads(kwargs['data'])['processDefinitionId'],
                     settings.FLOWABLE_SCAN_APP_ID)
        vars = json.loads(kwargs['data'])['variables']
        assert_equal([v for v in vars if v['name'] == 'projectId'][0], {
          'name': 'projectId',
          'type': 'string',
          'value': self.project._id
        })
        assert_equal([v for v in vars if v['name'] == 'paperFolderPattern'][0], {
          'name': 'paperFolderPattern',
          'type': 'string',
          'value': 'check/fake_labo_name/%-{}/'.format(self.project._id)
        })

    @mock.patch.object(IQBRIMSFlowableClient, '_make_request')
    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_set_status_to_custom_deposit(self, mock_get_management_node,
                                          mock_import_auth_from_management_node,
                                          mock_iqbrims_init_folders,
                                          mock_update_spreadsheet,
                                          mock_workflow_user_settings,
                                          mock_flowable_make_request):
        status = {
            'state': 'deposit',
            'labo_id': 'fake_labo_name',
            'other_attribute': 'fake_other_attribute',
            'is_dirty': False
        }
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        fake_management_project = ProjectFactory(creator=self.user)
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_client = mock.MagicMock()
        mock_iqbrims_init_folders.return_value = mock_client, fake_folder
        mock_update_spreadsheet.return_value = None
        user_settings = {'FLOWABLE_HOST': 'https://test.somehost.ac.jp/',
                         'FLOWABLE_RESEARCH_APP_ID': 'latest_workflow_id'}
        mock_workflow_user_settings.return_value = {'settings': user_settings}
        mock_flowable_make_request.return_value = MockResponse('{"test": 1}',
                                                               200)

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
        assert_equal(mock_import_auth_from_management_node.call_args[0], (
            self.project,
            iqbrims,
            fake_management_project
        ))

        assert_equal(mock_iqbrims_init_folders.call_count, 1)
        assert_equal(mock_iqbrims_init_folders.call_args[0], (
            self.project,
            fake_management_project,
            status['state'],
            status['labo_id']
        ))

        assert_equal(mock_update_spreadsheet.call_count, 1)
        assert_equal(mock_update_spreadsheet.call_args[0], (
            self.project,
            fake_management_project,
            status['state'],
            payload['data']['attributes']
        ))

        assert_equal(mock_flowable_make_request.call_count, 1)
        name, args, kwargs = mock_flowable_make_request.mock_calls[0]
        assert_equal(args, ('POST', 'https://test.somehost.ac.jp/' +
                                    'service/runtime/process-instances'))
        assert_equal(json.loads(kwargs['data'])['processDefinitionId'],
                     'latest_workflow_id')
        vars = json.loads(kwargs['data'])['variables']
        assert_equal([v for v in vars if v['name'] == 'projectId'][0], {
          'name': 'projectId',
          'type': 'string',
          'value': self.project._id
        })
        assert_equal([v for v in vars if v['name'] == 'paperFolderPattern'][0], {
          'name': 'paperFolderPattern',
          'type': 'string',
          'value': 'deposit/fake_labo_name/%-{}/'.format(self.project._id)
        })


class TestStorageViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestStorageViews, self).setUp()
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
        self.mock_fetch = mock.patch.object(
            self.node_settings.__class__,
            'fetch_access_token'
        )
        self.mock_fetch.return_value = self.external_account.oauth_key
        self.mock_fetch.start()

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_fetch.stop()
        super(TestStorageViews, self).tearDown()

    def test_unauthorized_get_storage(self):
        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='paper')
        res = self.app.delete(url,
                              expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='paper')
        res = self.app.delete(url, headers={'X-RDM-Token': 'invalid123'},
                              expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'get_column_values')
    @mock.patch.object(SpreadsheetClient, 'get_row_values')
    def test_get_index_storage(self, mock_get_row_values,
                               mock_get_column_values, mock_sheets,
                               mock_get_content, mock_files, mock_folders,
                               mock_get_management_node,
                               mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'filesheet',
                                    'title': 'Raw Files'},
                                   {'id': 'fileidlist',
                                    'title': '.files.txt'}]
        mock_get_content.return_value = b'dummy.txt'
        sgp = {'columnCount': 2}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456',
                                                    'gridProperties': sgp}}]
        mock_get_column_values.return_value = ['Filled']
        mock_get_row_values.return_value = ['FALSE']
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.status = json.dumps({'testkey': 'testvalue'})
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='index')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'processing')
        assert_equal(res.json['whole']['testkey'], 'testvalue')

        mock_get_column_values.assert_called_once()
        cargs, _ = mock_get_column_values.call_args
        assert_equal(cargs[0], 'Management')
        mock_get_row_values.assert_called_once()
        mock_sheets.assert_called_once()

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'get_column_values')
    @mock.patch.object(SpreadsheetClient, 'get_row_values')
    def test_get_index_storage_custom_sheet(self, mock_get_row_values,
                                            mock_get_column_values, mock_sheets,
                                            mock_get_content, mock_files,
                                            mock_folders,
                                            mock_get_management_node,
                                            mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'filesheet',
                                    'title': 'Raw Files'},
                                   {'id': 'fileidlist',
                                    'title': '.files.txt'}]
        mock_get_content.return_value = b'dummy.txt'
        sgp = {'columnCount': 2}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123',
                                                    'gridProperties': sgp}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456'}}]
        mock_get_column_values.return_value = ['Filled']
        mock_get_row_values.return_value = ['FALSE']
        user_settings = {'INDEXSHEET_MANAGEMENT_SHEET_NAME': 'Files'}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.status = json.dumps({'testkey': 'testvalue'})
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='index')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'processing')
        assert_equal(res.json['whole']['testkey'], 'testvalue')

        mock_get_column_values.assert_called_once()
        cargs, _ = mock_get_column_values.call_args
        assert_equal(cargs[0], 'Files')
        mock_get_row_values.assert_called_once()
        mock_sheets.assert_called_once()

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    def test_get_checklist_storage(self, mock_get_content, mock_files, mock_folders,
                                   mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'チェックリスト'}]
        mock_files.return_value = [{'id': 'fileid123',
                                    'title': 'dummy.txt'},
                                   {'id': 'fileidlist',
                                    'title': '.files.txt'}]
        mock_get_content.return_value = b'dummy.txt'

        node_settings = self.project.get_addon('iqbrims')
        node_settings.status = json.dumps({'testkey': 'testvalue'})
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='checklist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'complete')
        assert_equal(res.json['whole']['testkey'], 'testvalue')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    def test_get_checklist_ja_storage(self, mock_get_content, mock_files, mock_folders,
                                      mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'チェックリスト',
                                      'alternateLink': 'https://google/folderid123/'}]
        mock_files.return_value = [{'id': 'fileid123',
                                    'title': u'ダミー.txt'},
                                   {'id': 'fileidlist',
                                    'title': '.files.txt'}]
        mock_get_content.return_value = u'ダミー.txt\n\n'.encode('utf8')

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = u'testgdpath/日本語123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='checklist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'complete')
        assert_equal(res.json['folder_drive_url'], 'https://google/folderid123/')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    def test_get_checklist_ja_storage_partial(self, mock_get_content, mock_files,
                                              mock_folders, mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'チェックリスト'}]
        mock_files.return_value = [{'id': 'fileid123',
                                    'title': u'ダミー.txt'},
                                   {'id': 'fileidlist',
                                    'title': '.files.txt'}]
        mock_get_content.return_value = u'ダミー.txt\nダミー2.txt\n\n'.encode('utf8')

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = u'testgdpath/日本語123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='checklist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'processing')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_get_imagelist_storage(self, mock_files, mock_folders,
                                   mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        def mock_folders_effect(folder_id):
            if folder_id == '1234567890':
                return [{'id': 'folderid123', 'title': u'最終原稿・組図',
                         'alternateLink': 'https://google/folderid123/'}]
            if folder_id == 'folderid123':
                return [{'id': 'folderid456', 'title': u'スキャン画像',
                         'alternateLink': 'https://google/folderid456/'}]
            assert False, folder_id

        def mock_files_effect(folder_id):
            if folder_id == 'folderid123':
                return [{'id': 'fileid456b', 'title': 'files.txt',
                         'alternateLink': 'https://google/fileid456b/'}]
            if folder_id == 'folderid456':
                return [{'id': 'fileid456a', 'title': 'test.png',
                         'alternateLink': 'https://google/fileid456a/'}]
            assert False, folder_id

        mock_folders.side_effect = mock_folders_effect
        mock_files.side_effect = mock_files_effect

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='imagelist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'complete')
        assert_equal(res.json['folder_drive_url'], 'https://google/folderid456/')
        assert_equal(len(res.json['management']['urls']), 1)
        assert_equal(res.json['management']['urls'][0]['path'], u'iqb123/%E6%9C%80%E7%B5%82%E5%8E%9F%E7%A8%BF%E3%83%BB%E7%B5%84%E5%9B%B3/files.txt')
        assert_true(res.json['management']['urls'][0]['mfr_url'].startswith('http://localhost:7778/export?url=http://localhost:5000/'))
        assert_equal(res.json['management']['urls'][0]['drive_url'], 'https://google/fileid456b/')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_get_working_imagelist_storage_1(self, mock_files, mock_folders,
                                             mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        def mock_folders_effect(folder_id):
            if folder_id == '1234567890':
                return [{'id': 'folderid123', 'title': u'最終原稿・組図'}]
            if folder_id == 'folderid123':
                return []
            assert False, folder_id

        def mock_files_effect(folder_id):
            if folder_id == 'folderid123':
                return []
            if folder_id == 'folderid456':
                return [{'id': 'fileid456b', 'title': 'files.txt'}]
            assert False, folder_id

        mock_folders.side_effect = mock_folders_effect
        mock_files.side_effect = mock_files_effect

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='imagelist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'processing')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_get_working_imagelist_storage_2(self, mock_files, mock_folders,
                                             mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        def mock_folders_effect(folder_id):
            if folder_id == '1234567890':
                return [{'id': 'folderid123', 'title': u'最終原稿・組図'}]
            if folder_id == 'folderid123':
                return [{'id': 'folderid456', 'title': u'スキャン画像'}]
            assert False, folder_id

        def mock_files_effect(folder_id):
            if folder_id == 'folderid123':
                return []
            if folder_id == 'folderid456':
                return [{'id': 'fileid456a', 'title': 'test.png'}]
            assert False, folder_id

        mock_folders.side_effect = mock_folders_effect
        mock_files.side_effect = mock_files_effect

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='imagelist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['status'], 'processing')

    def test_unauthorized_reject_storage(self):
        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='paper')
        res = self.app.delete(url,
                              expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='paper')
        res = self.app.delete(url, headers={'X-RDM-Token': 'invalid123'},
                              expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'create_folder')
    @mock.patch.object(IQBRIMSClient, 'rename_folder')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_reject_checklist_storage(self, mock_files, mock_folders,
                                      mock_rename_folder, mock_create_folder,
                                      mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'チェックリスト'}]
        mock_files.return_value = [{'id': 'file123', 'title': 'test1.pdf'},
                                   {'id': 'file456', 'title': 'test2.pdf'}]

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='checklist')
        res = self.app.delete(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)

        assert_equal(res.json['status'], 'rejected')
        mock_rename_folder.assert_called_once()
        cargs, _ = mock_rename_folder.call_args
        assert_equal(cargs[0], 'rmfolderid123')
        foldername = cargs[1]
        assert_true(re.match(r'(.*)\.[0-9]+\-[0-9]+',
                             foldername).group(1) == u'チェックリスト')
        mock_create_folder.assert_called_once()
        assert_equal(mock_create_folder.call_args,
                     (('1234567890', u'チェックリスト'),))

        folderurlpath = '/' + quote(foldername.encode('utf8'))
        assert_equal(res.json['management']['id'], management_project._id)
        assert_equal(len(res.json['management']['urls']), 2)
        assert_equal(res.json['management']['urls'][0]['title'], 'test1.pdf')
        assert_true(res.json['management']['urls'][0]['url'].endswith(folderurlpath + '/test1.pdf'))
        assert_equal(res.json['management']['urls'][1]['title'], 'test2.pdf')
        assert_true(res.json['management']['urls'][1]['url'].endswith(folderurlpath + '/test2.pdf'))
        assert_equal(len(res.json['urls']), 2)
        assert_equal(res.json['urls'][0]['title'], 'test1.pdf')
        assert_true(res.json['urls'][0]['url'].endswith(folderurlpath + '/test1.pdf'))
        assert_equal(res.json['urls'][1]['title'], 'test2.pdf')
        assert_true(res.json['urls'][1]['url'].endswith(folderurlpath + '/test2.pdf'))
        assert_equal(res.json['root_folder'], 'iqb123/')

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'get_column_values')
    @mock.patch.object(SpreadsheetClient, 'update_row')
    def test_reject_index_storage(self, mock_update_row,
                                  mock_get_column_values, mock_sheets,
                                  mock_grant_access_from_anyone,
                                  mock_files, mock_folders,
                                  mock_get_management_node,
                                  mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'rmfileid123', 'title': 'Raw Files'}]
        sgp = {'columnCount': 2}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456',
                                                    'gridProperties': sgp}}]
        mock_get_column_values.return_value = ['Filled']
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='index')
        res = self.app.delete(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'rejected',
                                'root_folder': 'iqb123/'})
        mock_update_row.assert_called_once()
        assert_equal(mock_update_row.call_args, (('Management', ['FALSE'], 0),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('rmfileid123',),))

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'get_column_values')
    @mock.patch.object(SpreadsheetClient, 'update_row')
    def test_reject_index_storage_custom_sheet(self, mock_update_row,
                                               mock_get_column_values,
                                               mock_sheets,
                                               mock_grant_access_from_anyone,
                                               mock_files, mock_folders,
                                               mock_get_management_node,
                                               mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'rmfileid123', 'title': 'Raw Files'}]
        sgp = {'columnCount': 2}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123',
                                                    'gridProperties': sgp}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456',
                                                    'gridProperties': sgp}}]
        mock_get_column_values.return_value = ['Filled']
        user_settings = {'INDEXSHEET_MANAGEMENT_SHEET_NAME': 'Files'}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_reject_storage',
                                       folder='index')
        res = self.app.delete(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'rejected',
                                'root_folder': 'iqb123/'})
        mock_update_row.assert_called_once()
        assert_equal(mock_update_row.call_args, (('Files', ['FALSE'], 0),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('rmfileid123',),))

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_create_index_in_progress(self, mock_files, mock_folders,
                                      mock_get_management_node,
                                      mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = []
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'processing'})

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'create_spreadsheet')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'add_files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(IQBRIMSClient, 'get_file_link')
    def test_create_index(self, mock_get_file_link,
                          mock_grant_access_from_anyone, mock_add_files,
                          mock_sheets, mock_create_spreadsheet,
                          mock_files, mock_folders, mock_get_content,
                          mock_get_management_node,
                          mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_get_content.return_value = b'f1.txt\nf2.txt\ntest/file3.txt\n'
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.txt'}]
        mock_create_spreadsheet.return_value = {'id': 'sheet123'}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456'}}]
        mock_grant_access_from_anyone.return_value = {}
        mock_get_file_link.return_value = 'https://a.b/sheet123'
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete',
                                'url': 'https://a.b/sheet123'})
        mock_get_content.assert_called_once()
        assert_equal(mock_get_content.call_args, (('fileid123',),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('sheet123',),))
        mock_add_files.assert_called_once()
        assert_equal(mock_add_files.call_args,
                     (('Files', 'ss123', 'Management', 'ss456',
                       ['f1.txt', 'f2.txt', 'test/file3.txt', '']),))

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'create_spreadsheet')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'add_files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(IQBRIMSClient, 'get_file_link')
    def test_create_index_custom_sheet(self, mock_get_file_link,
                                       mock_grant_access_from_anyone,
                                       mock_add_files,
                                       mock_sheets, mock_create_spreadsheet,
                                       mock_files, mock_folders,
                                       mock_get_content,
                                       mock_get_management_node,
                                       mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_get_content.return_value = b'f1.txt\nf2.txt\ntest/file3.txt\n'
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.txt'}]
        mock_create_spreadsheet.return_value = {'id': 'sheet123'}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456'}}]
        mock_grant_access_from_anyone.return_value = {}
        mock_get_file_link.return_value = 'https://a.b/sheet123'
        user_settings = {'INDEXSHEET_MANAGEMENT_SHEET_NAME': 'Files'}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete',
                                'url': 'https://a.b/sheet123'})
        mock_get_content.assert_called_once()
        assert_equal(mock_get_content.call_args, (('fileid123',),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('sheet123',),))
        mock_add_files.assert_called_once()
        assert_equal(mock_add_files.call_args,
                     (('Files', 'ss123', 'Files', 'ss123',
                       ['f1.txt', 'f2.txt', 'test/file3.txt', '']),))

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'create_spreadsheet')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'add_files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(IQBRIMSClient, 'get_file_link')
    def test_create_index_ja(self, mock_get_file_link,
                             mock_grant_access_from_anyone, mock_add_files,
                             mock_sheets, mock_create_spreadsheet,
                             mock_files, mock_folders, mock_get_content,
                             mock_get_management_node,
                             mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_get_content.return_value = u'f1.txt\nf2.txt\ntest/ファイル3.txt\n'.encode('utf8')
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.txt'}]
        mock_create_spreadsheet.return_value = {'id': 'sheet123'}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456'}}]
        mock_grant_access_from_anyone.return_value = {}
        mock_get_file_link.return_value = 'https://a.b/sheet123'
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete',
                                'url': 'https://a.b/sheet123'})
        mock_get_content.assert_called_once()
        assert_equal(mock_get_content.call_args, (('fileid123',),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('sheet123',),))
        mock_add_files.assert_called_once()
        assert_equal(mock_add_files.call_args,
                     (('Files', 'ss123', 'Management', 'ss456',
                       ['f1.txt', 'f2.txt', u'test/ファイル3.txt', '']),))

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'get_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'copy_file')
    @mock.patch.object(SpreadsheetClient, 'sheets')
    @mock.patch.object(SpreadsheetClient, 'add_files')
    @mock.patch.object(IQBRIMSClient, 'grant_access_from_anyone')
    @mock.patch.object(IQBRIMSClient, 'get_file_link')
    def test_create_index_template(self, mock_get_file_link,
                                   mock_grant_access_from_anyone, mock_add_files,
                                   mock_sheets, mock_copy_file,
                                   mock_files, mock_folders, mock_get_content,
                                   mock_get_management_node,
                                   mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_get_content.return_value = u'f1.txt\nf2.txt\ntest/ファイル3.txt\n'.encode('utf8')
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.txt'}]
        mock_copy_file.return_value = {'id': 'sheet123'}
        mock_sheets.return_value = [{'properties': {'title': 'Files',
                                                    'sheetId': 'ss123'}},
                                    {'properties': {'title': 'Management',
                                                    'sheetId': 'ss456'}}]
        mock_grant_access_from_anyone.return_value = {}
        mock_get_file_link.return_value = 'https://a.b/sheet123'
        user_settings = {'FLOWABLE_DATALIST_TEMPLATE_ID': '1234567890'}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_index',
                                       folder='scan')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete',
                                'url': 'https://a.b/sheet123'})
        mock_get_content.assert_called_once()
        assert_equal(mock_get_content.call_args, (('fileid123',),))
        mock_grant_access_from_anyone.assert_called_once()
        assert_equal(mock_grant_access_from_anyone.call_args,
                     (('sheet123',),))
        mock_add_files.assert_called_once()
        assert_equal(mock_add_files.call_args,
                     (('Files', 'ss123', 'Management', 'ss456',
                       ['f1.txt', 'f2.txt', u'test/ファイル3.txt', '']),))
        mock_copy_file.assert_called_once()

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'create_content')
    @mock.patch.object(IQBRIMSClient, 'update_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_create_new_filelist(self, mock_files, mock_folders,
                                 mock_update_content, mock_create_content,
                                 mock_get_management_node,
                                 mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.zip'}]
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_filelist',
                                       folder='raw')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})

        mock_create_content.assert_called_once()
        assert_equal(mock_create_content.call_args,
                     (('folderid123', '.files.txt', 'text/plain', b'files.zip\n'),))

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'create_content')
    @mock.patch.object(IQBRIMSClient, 'update_content')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_create_exists_filelist(self, mock_files, mock_folders,
                                    mock_update_content, mock_create_content,
                                    mock_get_management_node,
                                    mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'files.zip'},
                                   {'id': 'fileid456', 'title': '.files.txt'}]
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_create_filelist',
                                       folder='raw')
        res = self.app.put(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})

        mock_update_content.assert_called_once()
        assert_equal(mock_update_content.call_args,
                     (('fileid456', 'text/plain', b'files.zip\n'),))

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_get_storage_no_comment(self, mock_files, mock_folders,
                                   mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'チェックリスト'}]
        mock_files.return_value = [{'id': 'fileid123',
                                    'title': 'dummy.txt'}]

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.status = json.dumps({'state': 'deposit',
                                           'labo_id': 'labox'})
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='checklist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['comment'], '')

    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    def test_get_storage_comment(self, mock_files, mock_folders,
                                   mock_get_management_node):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'folderid123',
                                      'title': u'チェックリスト'}]
        mock_files.return_value = [{'id': 'fileid123',
                                    'title': 'dummy.txt'}]

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.status = json.dumps({'state': 'deposit',
                                           'labo_id': 'labox',
                                           'checklist_comment': 'C1234'})
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_storage',
                                       folder='checklist')
        res = self.app.get(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['comment'], 'C1234')

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'revoke_access_from_anyone')
    def test_close_index_all(self, mock_revoke_access_from_anyone,
                             mock_files, mock_folders,
                             mock_get_management_node,
                             mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'Raw Files'}]
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_close_index')
        res = self.app.delete(url, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        mock_revoke_access_from_anyone.assert_called_once()
        name, args, kwargs = mock_revoke_access_from_anyone.mock_calls[0]
        assert_equal(args, ('fileid123',))
        assert_equal(kwargs, {'drop_all': 1})

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    @mock.patch.object(IQBRIMSClient, 'folders')
    @mock.patch.object(IQBRIMSClient, 'files')
    @mock.patch.object(IQBRIMSClient, 'revoke_access_from_anyone')
    def test_close_index_read(self, mock_revoke_access_from_anyone,
                              mock_files, mock_folders,
                              mock_get_management_node,
                              mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('googledrive', auth=None)
        gdsettings = management_project.get_addon('googledrive')
        gdsettings.folder_path = 'testgdpath/'
        gdsettings.save()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        mock_folders.return_value = [{'id': 'rmfolderid123',
                                      'title': u'生データ'}]
        mock_files.return_value = [{'id': 'fileid123', 'title': 'Raw Files'}]
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.folder_path = 'testgdpath/iqb123/'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_close_index')
        res = self.app.delete(url + '?all=0', headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        name, args, kwargs = mock_revoke_access_from_anyone.mock_calls[0]
        assert_equal(args, ('fileid123',))
        assert_equal(kwargs, {'drop_all': 0})


class TestNotificationViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestNotificationViews, self).setUp()
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
        self.project.contributors[0].emails.create(address='researcher@test.somehost.com')

    def tearDown(self):
        self.mock_about.stop()
        self.mock_get_folder_info.stop()
        self.mock_rename_folder.stop()
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
    def test_post_notify_jpn_without_mail(self, mock_get_management_node):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'notify_title': u'日本語',
          'notify_body': u'日本語'
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_without_mail(self, mock_get_management_node,
                                      mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_user_without_mail(self, mock_get_management_node,
                                           mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['user']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 0)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_adm_without_mail(self, mock_get_management_node,
                                          mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 0)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_adm_with_log(self, mock_get_management_node,
                                      mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'imagescan_workflow_start',
          'to': ['admin']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        assert_equal(management_project.logs.count(), 2)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 0)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_user_with_log(self, mock_get_management_node,
                                      mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'imagescan_workflow_start',
          'to': ['user']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 3)
        assert_equal(management_project.logs.count(), 2)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 0)
        assert mock_send_mail.call_args is None

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_with_mail(self, mock_get_management_node,
                                   mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert_equal(len(mock_send_mail.call_args_list), 2)
        assert_equal(mock_send_mail.call_args_list[0][0][0], self.project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['cc_addr'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['replyto'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[1][0][0], management_project.contributors[0].emails.all()[0].address)
        assert_true(mock_send_mail.call_args_list[1][1]['cc_addr'] is None)
        assert_true(mock_send_mail.call_args_list[1][1]['replyto'] is None)

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_with_multiple_mail(self, mock_get_management_node,
                                            mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        self.project.contributors[0].emails.create(address='researcher.sub@test.somehost.com')

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert_equal(len(mock_send_mail.call_args_list), 2)
        assert_equal(mock_send_mail.call_args_list[0][0][0], ','.join([email.address for email in self.project.contributors[0].emails.all()]))
        assert_equal(mock_send_mail.call_args_list[0][1]['cc_addr'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['replyto'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[1][0][0], management_project.contributors[0].emails.all()[0].address)
        assert_true(mock_send_mail.call_args_list[1][1]['cc_addr'] is None)
        assert_true(mock_send_mail.call_args_list[1][1]['replyto'] is None)

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_with_multiple_mgmt_mail(self, mock_get_management_node,
                                            mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        management_project.contributors[0].emails.create(address='staff.sub@test.somehost.com')

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert_equal(len(mock_send_mail.call_args_list), 2)
        assert_equal(mock_send_mail.call_args_list[0][0][0], self.project.contributors[0].emails.all()[0].address)
        assert_equal(set(mock_send_mail.call_args_list[0][1]['cc_addr'].split(',')), set([m.address for m in management_project.contributors[0].emails.all()]))
        assert_equal(mock_send_mail.call_args_list[0][1]['replyto'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[1][0][0], ','.join([m.address for m in management_project.contributors[0].emails.all()]))
        assert_true(mock_send_mail.call_args_list[1][1]['cc_addr'] is None)
        assert_true(mock_send_mail.call_args_list[1][1]['replyto'] is None)

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_body(self, mock_get_management_node, mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        body_html = u'''こんにちは。<br>
連絡です。<br>

URL: <a href="http://test.test">http://test.test</a><br>
文末。
'''
        comment_html = u'''**iqbrims_test_notify** こんにちは。<br>
連絡です。<br>

URL: http://test.test<br>
文末。
'''
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'notify_body': body_html,
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        assert user_comments.get().content == comment_html
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert admin_comments.get().content == comment_html
        assert_equal(len(mock_send_mail.call_args_list), 2)
        assert_equal(mock_send_mail.call_args_list[0][0][0], self.project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['cc_addr'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['replyto'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[1][0][0], management_project.contributors[0].emails.all()[0].address)
        assert_true(mock_send_mail.call_args_list[1][1]['cc_addr'] is None)
        assert_true(mock_send_mail.call_args_list[1][1]['replyto'] is None)

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_too_large_body(self, mock_get_management_node, mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        body_html = ''.join([u'0123456789' for _ in range(0, 101)])
        comment_html = u'**iqbrims_test_notify** ' + body_html[:797] + '...'
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'to': ['admin', 'user'],
          'notify_body': body_html,
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 1)
        assert user_comments.get().content == comment_html
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert admin_comments.get().content == comment_html
        assert_equal(len(mock_send_mail.call_args_list), 2)
        assert_equal(mock_send_mail.call_args_list[0][0][0], self.project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['cc_addr'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['replyto'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[1][0][0], management_project.contributors[0].emails.all()[0].address)
        assert_true(mock_send_mail.call_args_list[1][1]['cc_addr'] is None)
        assert_true(mock_send_mail.call_args_list[1][1]['replyto'] is None)

    @mock.patch.object(iqbrims_views, 'send_mail')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_notify_with_comments(self, mock_get_management_node,
                                   mock_send_mail):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_notify')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'comment_to': ['admin'],
          'email_to': ['user'],
          'use_mail': True,
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'status': 'complete'})
        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        user_comments = Comment.objects.filter(node=self.project)
        assert_equal(user_comments.count(), 0)
        admin_comments = Comment.objects.filter(node=management_project)
        assert_equal(admin_comments.count(), 1)
        assert_equal(len(mock_send_mail.call_args_list), 1)
        assert_equal(mock_send_mail.call_args_list[0][0][0], self.project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['cc_addr'], management_project.contributors[0].emails.all()[0].address)
        assert_equal(mock_send_mail.call_args_list[0][1]['replyto'], management_project.contributors[0].emails.all()[0].address)

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_undefined_message(self, mock_get_management_node, mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        user_settings = {}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_message')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'variables': {},
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {'notify_type': 'test_notify'})

    @mock.patch.object(IQBRIMSWorkflowUserSettings, 'load')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_defined_message(self, mock_get_management_node, mock_workflow_user_settings):
        management_project = ProjectFactory()
        management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = management_project
        user_settings = {'MESSAGES': json.dumps({
          'test_notify': {
            'notify_body': 'Variable #1 is ${var1}, Variable #2 is ${var2}',
            'user_email': True,
          }
        })}
        mock_workflow_user_settings.return_value = {'settings': user_settings}

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        url = self.project.api_url_for('iqbrims_get_message')
        res = self.app.post_json(url, {
          'notify_type': 'test_notify',
          'variables': {'var1': 'Variable #1', 'var2': None},
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json['notify_type'], 'test_notify')
        assert_equal(res.json['notify_body'], 'Variable #1 is Variable #1, Variable #2 is null')
        assert_equal(res.json['user_email'], True)


class TestWorkflowStateViews(IQBRIMSAddonTestCase, OsfTestCase):

    def setUp(self):
        super(TestWorkflowStateViews, self).setUp()
        self.project.contributors[0].emails.create(address='researcher@test.somehost.com')

    def tearDown(self):
        super(TestWorkflowStateViews, self).tearDown()

    def test_unauthorized_post_workflow_state(self):
        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()

        url = self.project.api_url_for('iqbrims_post_workflow_state',
                                       part='raw')
        res = self.app.post(url,
                            expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

        url = self.project.api_url_for('iqbrims_post_workflow_state',
                                       part='raw')
        res = self.app.post(url, headers={'X-RDM-Token': 'invalid123'},
                            expect_errors=True).maybe_follow()

        assert_equal(res.status_code, 403)

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_minimal_workflow_state(self, mock_get_management_node):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_workflow_state',
                                       part='raw')
        res = self.app.post_json(url, {
          'state': 'test',
          'permissions': ['READ', 'WRITE']
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
          'status': 'complete',
          'data': {
            'state': 'initialized',
            'workflow_raw_state': 'test',
            'workflow_raw_permissions': ['READ', 'WRITE']
          }
        })

    @mock.patch.object(IQBRIMSClient, 'get_folder_info')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_uploadable_workflow_state(self, mock_get_management_node,
                                            mock_import_auth_from_management_node,
                                            mock_iqbrims_init_folders, mock_update_spreadsheet,
                                            mock_get_folder_info):
        fake_management_project = ProjectFactory()
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_client = mock.MagicMock()
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        mock_iqbrims_init_folders.return_value = mock_client, fake_folder
        mock_update_spreadsheet.return_value = None
        mock_client.folders.return_value = [{
            'id': 'FOLDER12345',
            'title': '生データ',
        }]
        mock_get_folder_info.return_value = {
            'title': u'{0}-{1}'.format(self.project.title.replace('/', '_'), self.project._id)
        }

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.set_status({
            'state': 'deposit',
            'labo_id': 'fake_labo_name',
        })
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(fake_management_project.logs.count(), 2)
        url = self.project.api_url_for('iqbrims_post_workflow_state',
                                       part='raw')
        res = self.app.post_json(url, {
          'state': 'test',
          'permissions': ['READ', 'WRITE', 'UPLOADABLE']
        }, headers={'X-RDM-Token': token})

        assert_equal(len(mock_client.grant_access_from_anyone.call_args_list), 1)
        assert_equal(mock_client.grant_access_from_anyone.call_args_list[0][0][0], 'FOLDER12345')
        assert_equal(len(mock_client.revoke_access_from_anyone.call_args_list), 0)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
          'status': 'complete',
          'data': {
            'labo_id': 'fake_labo_name',
            'state': 'deposit',
            'workflow_raw_state': 'test',
            'workflow_raw_permissions': ['READ', 'WRITE', 'UPLOADABLE']
          }
        })

    @mock.patch.object(IQBRIMSClient, 'get_folder_info')
    @mock.patch.object(iqbrims_views, '_iqbrims_update_spreadsheet')
    @mock.patch.object(iqbrims_views, '_iqbrims_init_folders')
    @mock.patch.object(iqbrims_views, '_iqbrims_import_auth_from_management_node')
    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_prevent_uploadable_workflow_state(self, mock_get_management_node,
                                                    mock_import_auth_from_management_node,
                                                    mock_iqbrims_init_folders,
                                                    mock_update_spreadsheet,
                                                    mock_get_folder_info):
        fake_management_project = ProjectFactory()
        fake_management_project.add_addon('iqbrims', auth=None)
        mock_get_management_node.return_value = fake_management_project
        mock_import_auth_from_management_node.return_value = None
        mock_client = mock.MagicMock()
        fake_folder = {
            'id': '382635482',
            'path': 'fake/folder/path'
        }
        mock_iqbrims_init_folders.return_value = mock_client, fake_folder
        mock_update_spreadsheet.return_value = None
        mock_client.folders.return_value = [{
            'id': 'FOLDER12345',
            'title': '生データ',
        }]
        mock_get_folder_info.return_value = {
            'title': u'{0}-{1}'.format(self.project.title.replace('/', '_'), self.project._id)
        }

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.set_status({
            'state': 'deposit',
            'labo_id': 'fake_labo_name',
            'workflow_raw_permissions': ['READ', 'WRITE', 'UPLOADABLE']
        })
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(fake_management_project.logs.count(), 2)
        url = self.project.api_url_for('iqbrims_post_workflow_state',
                                       part='raw')
        res = self.app.post_json(url, {
          'state': 'test',
          'permissions': ['READ', 'WRITE']
        }, headers={'X-RDM-Token': token})

        assert_equal(len(mock_client.revoke_access_from_anyone.call_args_list), 1)
        assert_equal(mock_client.revoke_access_from_anyone.call_args_list[0][0][0], 'FOLDER12345')
        assert_equal(len(mock_client.grant_access_from_anyone.call_args_list), 0)

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
          'status': 'complete',
          'data': {
            'labo_id': 'fake_labo_name',
            'state': 'deposit',
            'workflow_raw_state': 'test',
            'workflow_raw_permissions': ['READ', 'WRITE']
          }
        })

    @mock.patch.object(iqbrims_views, '_get_management_node')
    def test_post_custom_workflow_state(self, mock_get_management_node):
        management_project = ProjectFactory()
        mock_get_management_node.return_value = management_project

        node_settings = self.project.get_addon('iqbrims')
        node_settings.secret = 'secret123'
        node_settings.process_definition_id = 'process456'
        node_settings.save()
        token = hashlib.sha256(('secret123' + 'process456' +
                                self.project._id).encode('utf8')).hexdigest()

        assert_equal(self.project.logs.count(), 2)
        assert_equal(management_project.logs.count(), 1)
        url = self.project.api_url_for('iqbrims_post_workflow_state',
                                       part='raw')
        res = self.app.post_json(url, {
          'state': 'test',
          'permissions': ['READ', 'WRITE'],
          'status': {'is_directly_submit_data': True}
        }, headers={'X-RDM-Token': token})

        assert_equal(res.status_code, 200)
        assert_equal(res.json, {
          'status': 'complete',
          'data': {
            'workflow_raw_state': 'test',
            'workflow_raw_permissions': ['READ', 'WRITE'],
            'state': 'initialized',
            'is_directly_submit_data': True
          }
        })
