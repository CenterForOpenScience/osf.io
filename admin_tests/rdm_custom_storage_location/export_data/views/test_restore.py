import json

import mock
import pytest
import requests
from celery import states
from celery.contrib.abortable import AbortableTask, AbortableAsyncResult
from celery.utils.threads import LocalStack
from django.db import IntegrityError
from nose import tools as nt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from admin.rdm_custom_storage_location.export_data.views import restore
from admin.rdm_custom_storage_location.export_data.views.restore import ProcessError
from framework.celery_tasks import app as celery_app
from osf.models import RdmFileTimestamptokenVerifyResult, ExportData, FileVersion
from osf_tests.factories import (
    AuthUserFactory,
    ExportDataFactory,
    RegionFactory,
    OsfStorageFileFactory,
    ExportDataRestoreFactory,
    BaseFileNodeFactory,
    addon_waterbutler_settings,
    bulkmount_waterbutler_settings,
    UserFactory,
    ProjectFactory,
    InstitutionFactory,
    FileVersionFactory
)
from tests.base import AdminTestCase
from django.contrib.auth.models import AnonymousUser


FAKE_TASK_ID = '00000000-0000-0000-0000-000000000000'
RESTORE_EXPORT_DATA_PATH = 'admin.rdm_custom_storage_location.export_data.views.restore'
EXPORT_DATA_UTIL_PATH = 'admin.rdm_custom_storage_location.export_data.utils'
EXPORT_DATA_TASK_PATH = 'admin.rdm_custom_storage_location.tasks'


# Test cases for initializing ProcessError
@pytest.mark.feature_202210
def test_init_process_error():
    process_error = ProcessError(f'Test initialize process error object')
    nt.assert_equal(str(process_error), f'Test initialize process error object')


# Test cases for RestoreDataActionView
@pytest.mark.feature_202210
class TestRestoreDataActionView(AdminTestCase):
    def setUp(self):
        self.view = restore.RestoreDataActionView()
        self.export_data = ExportDataFactory()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.institution = InstitutionFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.view.kwargs = {
            'export_id': 1,
        }
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')
        self.region_inst_01 = RegionFactory(_id=self.institution01._id)
        self.region_inst_02 = RegionFactory(_id=self.institution02._id)
        self.export_data_01 = ExportDataFactory(source=self.region_inst_01)
        self.export_data_02 = ExportDataFactory(source=self.region_inst_02)

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

    def test_init(self):
        nt.assert_equal(self.view.kwargs.get('export_id'), 1)
        nt.assert_is_not_none(self.view.post)

    def test_post_missing_params(self):
        request = APIRequestFactory().post('restore_export_data', {})
        request.user = AuthUserFactory()
        self.view.request = request
        response = self.view.dispatch(request)
        nt.assert_equal(response.data, {'message': f'Missing required parameters.'})
        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_before_restore_export_data')
    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.check_for_any_running_restore_process')
    def test_post(self, mock_check_for_running_restore, mock_check_before_restore):
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': 1,
        })
        request.user = AuthUserFactory()
        mock_check_for_running_restore.return_value = False
        mock_check_before_restore.return_value = {'open_dialog': True}

        response = self.view.post(request)
        mock_check_for_running_restore.assert_called()
        mock_check_before_restore.assert_called()
        nt.assert_equal(response.data, {})
        nt.assert_equal(response.status_code, status.HTTP_200_OK)

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.Institution.load')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.prepare_for_restore_export_data_process')
    def test_post_after_confirm_dialog(self, mock_prepare_for_restore, mock_export_data, mock_institution):
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': 1,
            'is_from_confirm_dialog': True
        })
        request.user = AuthUserFactory()
        mock_institution.return_value = self.institution
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_prepare_for_restore.return_value = Response(
            {'task_id': FAKE_TASK_ID}, status=status.HTTP_200_OK)
        self.view.destination_id = self.region_inst_01.id
        self.view.export_id = self.export_data.id
        self.view.export_data = self.export_data
        self.view.destination = self.region_inst_01
        response = self.view.post(request)
        mock_prepare_for_restore.assert_called()
        nt.assert_equal(response.data, {'task_id': FAKE_TASK_ID})
        nt.assert_equal(response.status_code, status.HTTP_200_OK)

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.Institution.load')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.prepare_for_restore_export_data_process')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_before_restore_export_data')
    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.check_for_any_running_restore_process')
    def test_post_without_confirm_dialog(self, mock_check_for_running_restore, mock_check_before_restore, mock_prepare_for_restore, mock_export_data,
                                         mock_institution):
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': 1,
        })
        request.user = AuthUserFactory()
        mock_institution.return_value = self.institution
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_check_for_running_restore.return_value = False
        mock_check_before_restore.return_value = {}
        mock_prepare_for_restore.return_value = Response(
            {'task_id': FAKE_TASK_ID}, status=status.HTTP_200_OK)
        self.view.destination_id = self.region_inst_01.id
        self.view.export_id = self.export_data.id
        self.view.export_data = self.export_data
        self.view.destination = self.region_inst_01
        response = self.view.post(request)
        mock_check_for_running_restore.assert_called()
        mock_check_before_restore.assert_called()
        mock_prepare_for_restore.assert_called()
        nt.assert_equal(response.data, {'task_id': FAKE_TASK_ID})
        nt.assert_equal(response.status_code, status.HTTP_200_OK)

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.check_for_any_running_restore_process')
    def test_post_already_running(self, mock_check_for_running_restore):
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': 1,
        })
        request.user = AuthUserFactory()
        mock_check_for_running_restore.return_value = True

        response = self.view.post(request)
        mock_check_for_running_restore.assert_called()
        nt.assert_equal(response.data, {'message': f'Cannot restore in this time.'})
        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_before_restore_export_data')
    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.check_for_any_running_restore_process')
    def test_post_return_error_message(self, mock_check_for_running_restore, mock_check_before_restore):
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': 1,
        })
        request.user = AuthUserFactory()
        mock_check_for_running_restore.return_value = False
        mock_check_before_restore.return_value = {'open_dialog': False, 'message': f'Mock test error message.'}

        response = self.view.post(request)
        mock_check_for_running_restore.assert_called()
        mock_check_before_restore.assert_called()
        nt.assert_equal(response.data, {'message': f'Mock test error message.'})
        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__test_func__anonymous(self):
        view = restore.RestoreDataActionView()
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.anon
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__normal_user(self):
        view = restore.RestoreDataActionView()
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.normal_user
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__super(self):
        view = restore.RestoreDataActionView()
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_01.id
        view.export_id = self.export_data_01.id
        view.export_data = self.export_data_01
        view.destination = self.region_inst_01
        nt.assert_equal(view.test_func(), True)

    def test__test_func__admin_with_permission(self):
        view = restore.RestoreDataActionView()
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_01.id
        view.export_id = self.export_data_01.id
        view.export_data = self.export_data_01
        view.destination = self.region_inst_01
        nt.assert_equal(view.test_func(), True)

    def test__test_func__admin_without_permission(self):
        view = restore.RestoreDataActionView()

        # not same institution of login user
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.institution02_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_01.id
        view.export_id = self.export_data_01.id
        view.export_data = self.export_data_01
        view.destination = self.region_inst_01
        nt.assert_equal(view.test_func(), False)

        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_02.id,
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.destination_id = self.region_inst_01.id
        view.export_id = self.export_data_02.id
        view.export_data = self.export_data_02
        view.destination = self.region_inst_01
        nt.assert_equal(view.test_func(), False)

        # admin not in institution
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_02.id,
        })
        self.institution02_admin.affiliated_institutions = []
        request.user = self.institution02_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__export_and_dest_not_same_inst(self):
        view = restore.RestoreDataActionView()
        request = APIRequestFactory().post('restore_export_data', {
            'destination_id': self.region_inst_02.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_02.id
        view.export_id = self.export_data_01.id
        view.export_data = self.export_data_01
        view.destination = self.region_inst_02
        nt.assert_equal(view.test_func(), False)


# Test cases for CheckTaskStatusRestoreDataActionView
@pytest.mark.feature_202210
class TestCheckTaskStatusRestoreDataActionView(AdminTestCase):
    def setUp(self):
        self.view = restore.CheckTaskStatusRestoreDataActionView()
        self.institution01 = InstitutionFactory(name='inst01')
        self.institution02 = InstitutionFactory(name='inst02')
        self.region_inst_01 = RegionFactory(_id=self.institution01._id)
        self.region_inst_02 = RegionFactory(_id=self.institution02._id)
        self.export_data_01 = ExportDataFactory(source=self.region_inst_01)
        self.export_data_02 = ExportDataFactory(source=self.region_inst_02)
        self.restore_data_01 = ExportDataRestoreFactory(export=self.export_data_01)
        self.restore_data_01.task_id = FAKE_TASK_ID + str(self.restore_data_01.id)
        self.restore_data_01.save()
        self.restore_data_02 = ExportDataRestoreFactory(export=self.export_data_02)
        self.restore_data_02.task_id = FAKE_TASK_ID + str(self.restore_data_02.id)
        self.restore_data_02.save()

        self.anon = AnonymousUser()

        self.normal_user = AuthUserFactory(fullname='normal_user')
        self.normal_user.is_staff = False
        self.normal_user.is_superuser = False

        self.superuser = AuthUserFactory(fullname='superuser')
        self.superuser.is_staff = True
        self.superuser.is_superuser = True
        self.superuser.save()

        self.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        self.institution01_admin.is_staff = True
        self.institution01_admin.affiliated_institutions.add(self.institution01)
        self.institution01_admin.save()

        self.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        self.institution02_admin.is_staff = True
        self.institution02_admin.affiliated_institutions.add(self.institution02)
        self.institution02_admin.save()

    def test_init(self):
        nt.assert_is_not_none(self.view.get)

    def test_get_success(self):
        request = APIRequestFactory().get('task_status', {
            'task_id': FAKE_TASK_ID,
            'task_type': 'Restore'
        })
        mock_async_result = mock.MagicMock()
        mock_async_result.return_value = {
            'status': states.SUCCESS,
            'result': None
        }
        with mock.patch('celery.contrib.abortable.AbortableAsyncResult._get_task_meta', mock_async_result):
            response = self.view.get(request)
            nt.assert_equal(response.data, {
                'state': states.SUCCESS,
                'task_id': FAKE_TASK_ID,
                'task_type': 'Restore'
            })
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_pending_with_result(self):
        request = APIRequestFactory().get('task_status', {
            'task_id': FAKE_TASK_ID,
            'task_type': 'Restore'
        })
        mock_async_result = mock.MagicMock()
        mock_async_result.return_value = {
            'status': states.PENDING,
            'result': {
                'current_progress_step': 1
            }
        }
        with mock.patch('celery.contrib.abortable.AbortableAsyncResult._get_task_meta', mock_async_result):
            response = self.view.get(request)
            nt.assert_equal(response.data, {
                'state': states.PENDING,
                'task_id': FAKE_TASK_ID,
                'task_type': 'Restore',
                'result': {
                    'current_progress_step': 1
                }
            })
            nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_get_missing_params(self):
        request = APIRequestFactory().get('task_status', {})
        response = self.view.get(request)
        nt.assert_equal(response.data, {'message': f'Missing required parameters.'})
        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__test_func__anonymous(self):
        view = restore.CheckTaskStatusRestoreDataActionView()
        request = APIRequestFactory().get('task_status', {
            'task_id': FAKE_TASK_ID,
            'task_type': 'Restore'
        })
        request.user = self.anon
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__normal_user(self):
        view = restore.CheckTaskStatusRestoreDataActionView()
        request = APIRequestFactory().get('task_status', {
            'task_id': FAKE_TASK_ID,
            'task_type': 'Restore'
        })
        request.user = self.normal_user
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__super(self):
        view = restore.CheckTaskStatusRestoreDataActionView()
        request = APIRequestFactory().get('task_status', {
            'task_id': self.restore_data_01.task_id,
            'task_type': 'Restore'
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), True)

    def test__test_func__admin_with_permission(self):
        view = restore.CheckTaskStatusRestoreDataActionView()
        request = APIRequestFactory().get('task_status', {
            'task_id': self.restore_data_01.task_id,
            'task_type': 'Restore'
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), True)

    def test__test_func__admin_without_permission(self):
        view = restore.CheckTaskStatusRestoreDataActionView()

        # not same institution of login user
        request = APIRequestFactory().get('task_status', {
            'task_id': self.restore_data_01.task_id,
            'task_type': 'Restore'
        })
        request.user = self.institution02_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        nt.assert_equal(view.test_func(), False)

        request = APIRequestFactory().get('task_status', {
            'task_id': self.restore_data_01.task_id,
            'task_type': 'Restore'
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        nt.assert_equal(view.test_func(), False)

        # admin not in institution
        request = APIRequestFactory().get('task_status', {
            'task_id': self.restore_data_01.task_id,
            'task_type': 'Restore'
        })
        self.institution01_admin.affiliated_institutions = []
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__without_param(self):
        view = restore.CheckTaskStatusRestoreDataActionView()
        request = APIRequestFactory().get('task_status', {})
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), True)


# Test cases for functions in restore.py used only in restore data process
@pytest.mark.feature_202210
class TestRestoreDataFunction(AdminTestCase):
    def setUp(self):
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })
        self.export_data = ExportDataFactory()
        self.export_data_restore = ExportDataRestoreFactory()
        self.region = RegionFactory()
        self.project_id = 'project_id'
        self.view = restore
        self.test_export_data_files = [
            {
                'id': 995,
                'path': '/630de9f5b71d8f06d918fbd7',
                'materialized_path': '/@ember-decorators/utils/collapse-proto.d.ts',
                'name': 'collapse-proto.d.ts',
                'provider': 'osfstorage',
                'created_at': '2023-04-18 04:40:25',
                'modified_at': '2023-04-18 04:40:25',
                'project': {
                    'id': 'pmockt',
                    'name': 'Project Mock'
                },
                'tags': ['hello', 'world'],
                'version': [
                    {
                        'identifier': '1',
                        'created_at': '2023-04-18 04:40:25',
                        'modified_at': '2023-04-18 04:40:25',
                        'size': 6000,
                        'version_name': 'collapse-proto.d.ts',
                        'metadata': {
                            'md5': '8c42361841f16989e0bf62a3ae408f1c',
                            'kind': 'file',
                            'sha256': 'ea070092664567d32e4524c6034214a293e75d0a53cfe9118f41e4752e97987c',
                        },
                        'location': {
                            'object': '64charsversion164charsversion164charsversion164charsversion164ch',
                            'provider': 's3compat'
                        },
                        'contributor': 'fake_user',
                    }
                ],
                'location': {},
                'timestamp': {},
                'checkout_id': None
            },
        ]
        addon_region = RegionFactory(waterbutler_settings=addon_waterbutler_settings)
        self.addon_data_restore = ExportDataRestoreFactory.create(destination=addon_region)

        bulkmount_region = RegionFactory(waterbutler_settings=bulkmount_waterbutler_settings)
        self.bulk_mount_data_restore = ExportDataRestoreFactory.create(destination=bulkmount_region)
        self.user = UserFactory()

    # check_before_restore_export_data
    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_empty_destination_storage(self, mock_read_export_data, mock_read_file_info, mock_utils_get_file_data):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({'data': []}).encode('utf-8')

        mock_read_export_data.return_value = True
        mock_read_file_info.return_value = {'folders': [{'project': {'id': self.project_id}}]}
        mock_utils_get_file_data.return_value = test_response

        result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                            self.addon_data_restore.destination.id)
        mock_read_export_data.assert_called()
        mock_read_file_info.assert_called()
        mock_utils_get_file_data.assert_called()
        nt.assert_equal(result, {'open_dialog': False})

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_bulk_mount_destination_storage(self, mock_read_export_data, mock_read_file_info, mock_utils_get_file_data):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({'data': []}).encode('utf-8')

        mock_read_export_data.return_value = True
        mock_read_file_info.return_value = {'folders': [{'project': {'id': self.project_id}}], 'files': [{'project': {'id': self.project_id}}]}
        mock_utils_get_file_data.return_value = test_response

        result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                            self.bulk_mount_data_restore.destination.id)
        mock_read_export_data.assert_called()
        mock_read_file_info.assert_called()
        mock_utils_get_file_data.assert_not_called()
        nt.assert_equal(result, {'open_dialog': False})

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_error_at_export_file(self, mock_read_export_data):
        mock_read_export_data.return_value = False

        result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                            self.addon_data_restore.destination.id)
        mock_read_export_data.assert_called()
        nt.assert_equal(result, {'open_dialog': False, 'message': f'The export data files are corrupted'})

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_exception_at_export_file(self, mock_read_export_data):
        mock_read_export_data.side_effect = Exception(f'Mock test exception at read export data file')

        result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                            self.addon_data_restore.destination.id)
        mock_read_export_data.assert_called()
        nt.assert_equal(result,
                        {'open_dialog': False,
                         'message': f'Cannot connect to the export data storage location'})

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_error_at_file_info(self, mock_read_export_data):
        mock_read_export_data.return_value = True
        mock_read_file_info = mock.MagicMock()
        mock_read_file_info.return_value = {}

        with mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema', mock_read_file_info):
            result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                                self.addon_data_restore.destination.id)
            mock_read_export_data.assert_called()
            mock_read_file_info.assert_called()
            nt.assert_equal(result, {'open_dialog': False, 'message': f'The export data files are corrupted'})

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_no_destination_region_found(self, mock_read_export_data):
        mock_read_export_data.return_value = True
        mock_read_file_info = mock.MagicMock()
        mock_read_file_info.return_value = {'folders': [{'project': {'id': self.project_id}}]}

        with mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema', mock_read_file_info):
            result = self.view.check_before_restore_export_data(None, self.export_data.id, -1)
            mock_read_export_data.assert_called()
            mock_read_file_info.assert_called()
            nt.assert_equal(result,
                            {'open_dialog': False, 'message': f'Failed to get destination storage information'})

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_error_at_check_destination_storage(self, mock_read_export_data, mock_read_file_info,
                                                                                 mock_utils_get_file_data):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_400_BAD_REQUEST
        test_response._content = json.dumps(
            {'message': f'Mock test bad request when check destination storage'}).encode('utf-8')

        mock_read_export_data.return_value = True
        mock_read_file_info.return_value = {'folders': [{'project': {'id': self.project_id}}]}
        mock_utils_get_file_data.return_value = test_response

        result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                            self.addon_data_restore.destination.id)
        mock_read_export_data.assert_called()
        mock_read_file_info.assert_called()
        mock_utils_get_file_data.assert_called()
        nt.assert_equal(result, {'open_dialog': False, 'message': f'Cannot connect to destination storage'})

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_not_empty_destination_storage(self, mock_read_export_data, mock_read_file_info, mock_utils_get_file_data):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({'data': [{}]}).encode('utf-8')

        mock_read_export_data.return_value = True
        mock_read_file_info.return_value = {'folders': [{'project': {'id': self.project_id}}]}
        mock_utils_get_file_data.return_value = test_response

        result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                            self.addon_data_restore.destination.id)
        mock_read_export_data.assert_called()
        mock_read_file_info.assert_called()
        mock_utils_get_file_data.assert_called()
        nt.assert_equal(result, {'open_dialog': True})

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.get_file_data')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_export_data_and_check_schema')
    def test_check_before_restore_export_data_exception_at_check_destination_storage(self, mock_read_export_data, mock_read_file_info,
                                                                                     mock_utils_get_file_data):
        mock_read_export_data.return_value = True
        mock_read_file_info.return_value = {'folders': [{'project': {'id': self.project_id}}]}
        mock_utils_get_file_data.side_effect = Exception('Mock test exception at check destination storage')

        result = self.view.check_before_restore_export_data(None, self.export_data.id,
                                                            self.addon_data_restore.destination.id)
        mock_read_export_data.assert_called()
        mock_read_file_info.assert_called()
        mock_utils_get_file_data.assert_called()
        nt.assert_equal(result, {'open_dialog': False, 'message': f'Cannot connect to destination storage'})

    # prepare_for_restore_export_data_process
    def test_prepare_for_restore_export_data_process_with_other_process_running(self):
        mock_utils = mock.MagicMock()
        mock_utils.return_value = True
        creator = self.user
        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.check_for_any_running_restore_process', mock_utils):
            response = self.view.prepare_for_restore_export_data_process(None, self.export_data.id,
                                                                         self.export_data_restore.destination.id, [], creator)
            mock_utils.assert_called()
            nt.assert_equal(response.data, {'message': f'Cannot restore in this time.'})
            nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prepare_for_restore_export_data_process_successfully(self):
        mock_utils = mock.MagicMock()
        mock_utils.return_value = False
        mock_task = mock.MagicMock()
        mock_task.return_value = AbortableAsyncResult(FAKE_TASK_ID)
        creator = self.user
        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.check_for_any_running_restore_process', mock_utils):
            with mock.patch(f'{EXPORT_DATA_TASK_PATH}.run_restore_export_data_process.delay', mock_task):
                response = self.view.prepare_for_restore_export_data_process(None, self.export_data.id,
                                                                             self.export_data_restore.destination.id, [], creator)
                mock_utils.assert_called()
                mock_task.assert_called()
                nt.assert_equal(response.data, {'task_id': FAKE_TASK_ID})
                nt.assert_equal(response.status_code, status.HTTP_200_OK)

    # restore_export_data_process
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.create_folder_in_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_tag_and_timestamp_to_database')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.copy_files_from_export_data_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    def test_restore_export_data_process(self, mock_read_file_info, mock_check_process, mock_copy_to_destination,
                                         mock_add_tag_and_timestamp, mock_create_folder_path):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_read_file_info.return_value = {'folders': [{'project': {'id': 1}}], 'files': [{'project': {'id': 1}}]}
        mock_check_process.return_value = None
        mock_copy_to_destination.return_value = [{}, []]
        mock_add_tag_and_timestamp.return_value = None
        mock_create_folder_path.return_value = None

        self.view.restore_export_data_process(task, {}, self.addon_data_restore.export.id,
                                              self.addon_data_restore.id, ['vcu'])
        mock_read_file_info.assert_called()
        mock_check_process.assert_called()
        mock_copy_to_destination.assert_called()
        mock_add_tag_and_timestamp.assert_called()

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.create_folder_in_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_tag_and_timestamp_to_database')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.copy_files_from_export_data_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    def test_restore_export_data_process_empty_file_info_list(self, mock_read_file_info, mock_check_process,
                                                              mock_copy_to_destination, mock_add_tag_and_timestamp, mock_create_folder_path):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_read_file_info.return_value = {}
        mock_check_process.return_value = None
        mock_copy_to_destination.return_value = [{}]
        mock_add_tag_and_timestamp.return_value = None
        mock_create_folder_path.return_value = None

        self.view.restore_export_data_process(task, {}, self.export_data_restore.export.id,
                                              self.export_data_restore.id, [])
        mock_read_file_info.assert_called()
        mock_check_process.assert_not_called()
        mock_copy_to_destination.assert_not_called()
        mock_add_tag_and_timestamp.assert_not_called()

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.create_folder_in_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_tag_and_timestamp_to_database')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.copy_files_from_export_data_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    def test_restore_export_data_process_bulk_mount_storage(
            self, mock_read_file_info, mock_check_process, mock_copy_to_destination,
            mock_add_tag_and_timestamp, mock_create_folder_path):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_read_file_info.return_value = {'folders': [{'project': {'id': 1}}], 'files': [{'project': {'id': 1}}]}
        mock_check_process.return_value = None
        mock_copy_to_destination.return_value = [{}, []]
        mock_add_tag_and_timestamp.return_value = None
        mock_create_folder_path.return_value = None

        self.view.restore_export_data_process(task, {}, self.bulk_mount_data_restore.export.id,
                                              self.bulk_mount_data_restore.id, ['vcu'])
        mock_read_file_info.assert_called()
        mock_check_process.assert_called()
        mock_copy_to_destination.assert_called()
        mock_add_tag_and_timestamp.assert_called()

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.create_folder_in_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_tag_and_timestamp_to_database')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.copy_files_from_export_data_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    def test_restore_export_data_process_abort_exception(self, mock_read_file_info, mock_check_process, mock_copy_to_destination,
                                                         mock_add_tag_and_timestamp, mock_create_folder_path):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID
        task_result = task.AsyncResult(FAKE_TASK_ID)

        def mock_callback_test_check_process_abort(*args, **kwargs):
            task_result.abort()
            raise ProcessError(f'Mock test abort process')

        mock_read_file_info.return_value = {'folders': [{'project': {'id': 1}}], 'files': [{'project': {'id': 1}}]}
        mock_check_process.side_effect = mock_callback_test_check_process_abort
        mock_copy_to_destination.return_value = [{}]
        mock_add_tag_and_timestamp.return_value = None
        mock_create_folder_path.return_value = None

        with nt.assert_raises(ProcessError):
            self.view.restore_export_data_process(task, {}, self.export_data_restore.export.id,
                                                  self.export_data_restore.id, [])
            mock_read_file_info.assert_called()
            mock_check_process.assert_called()
            mock_copy_to_destination.assert_not_called()
            mock_add_tag_and_timestamp.assert_not_called()

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.create_folder_in_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_tag_and_timestamp_to_database')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.copy_files_from_export_data_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.read_file_info_and_check_schema')
    def test_restore_export_data_process_other_exception(self, mock_read_file_info, mock_check_process, mock_copy_to_destination,
                                                         mock_add_tag_and_timestamp, mock_create_folder_path):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_read_file_info.return_value = {'folders': [{'project': {'id': 1}}], 'files': [{'project': {'id': 1}}]}
        mock_check_process.return_value = None
        mock_create_folder_path.return_value = None
        mock_copy_to_destination.return_value = [{}, []]
        mock_add_tag_and_timestamp.side_effect = IntegrityError(f'Mock test for error when adding tag/timestamp')

        with nt.assert_raises(IntegrityError):
            self.view.restore_export_data_process(task, {}, self.export_data_restore.export.id,
                                                  self.export_data_restore.id, [])
            mock_read_file_info.assert_called()
            mock_check_process.assert_called()
            mock_copy_to_destination.assert_called()
            mock_add_tag_and_timestamp.assert_called()

    # update_restore_process_state
    def test_update_restore_process_state(self):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID
        self.view.update_restore_process_state(task, 1)
        task_result = task.AsyncResult(FAKE_TASK_ID)
        nt.assert_equal(task_result.result.get('current_restore_step'), 1)

    # check_if_restore_process_stopped
    def test_check_if_restore_process_stopped_is_true(self):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID
        task_result = task.AsyncResult(FAKE_TASK_ID)
        task_result.abort()
        with nt.assert_raises(ProcessError):
            self.view.check_if_restore_process_stopped(task, 1)

    def test_check_if_restore_process_stopped_is_false(self):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID + '1'
        nt.assert_is_none(self.view.check_if_restore_process_stopped(task, 1))

    # add_tags_to_file_node
    def test_add_tags_to_file_node_empty_tags(self):
        node = OsfStorageFileFactory()
        clone_node = node.clone()
        self.view.add_tags_to_file_node(node, [])
        nt.assert_equal(node.tags.count(), 0)
        nt.assert_not_equal(clone_node, node)

    def test_add_tags_to_file_node_with_tags(self):
        tags = ['tag1', 'tag2']
        node = OsfStorageFileFactory()
        clone_node = node.clone()
        self.view.add_tags_to_file_node(node, tags)
        nt.assert_not_equal(clone_node, node)
        nt.assert_equal(node.tags.count(), 2)

    # add_timestamp_to_file_node
    def test_add_timestamp_to_file_node_missing_args(self):
        add_result = self.view.add_timestamp_to_file_node(None, None, None)
        nt.assert_is_none(add_result)

    def test_add_timestamp_to_file_node_existing_timestamp(self):
        node = OsfStorageFileFactory()
        project_id = 1
        timestamp = {
            'key_file_name': 'mocked.txt'
        }
        result = RdmFileTimestamptokenVerifyResult()
        result.save()
        add_result = self.view.add_timestamp_to_file_node(node, project_id, timestamp)
        nt.assert_is_none(add_result)

    def test_add_timestamp_to_file_node_new_timestamp(self):
        node = OsfStorageFileFactory()
        project_id = 1
        timestamp = {
            'key_file_name': 'mocked.txt'
        }
        add_result = self.view.add_timestamp_to_file_node(node, project_id, timestamp)
        nt.assert_is_none(add_result)

    # read_export_data_and_check_schema
    def test_read_export_data_and_check_schema_valid_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_read_export_data = mock.MagicMock()
        mock_read_export_data.return_value = test_response
        mock_validate_file_json = mock.MagicMock()
        mock_validate_file_json.return_value = True
        with mock.patch.object(ExportData, 'read_export_data_from_location', mock_read_export_data):
            with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.validate_file_json', mock_validate_file_json):
                result = self.view.read_export_data_and_check_schema(self.export_data, None)
                mock_read_export_data.assert_called_once()
                mock_validate_file_json.assert_called_once()
                nt.assert_equal(result, True)

    def test_read_export_data_and_check_schema_read_file_error(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_400_BAD_REQUEST
        test_response._content = json.dumps({}).encode('utf-8')

        mock_read_export_data = mock.MagicMock()
        mock_read_export_data.return_value = test_response
        with mock.patch.object(ExportData, 'read_export_data_from_location', mock_read_export_data):
            with nt.assert_raises(ProcessError):
                result = self.view.read_export_data_and_check_schema(self.export_data, None)
                mock_read_export_data.assert_called_once()
                nt.assert_is_none(result)

    def test_read_export_data_and_check_schema_read_file_exception(self):
        mock_read_export_data = mock.MagicMock()
        mock_read_export_data.side_effect = Exception(f'Mock test exception while reading export data')
        with mock.patch.object(ExportData, 'read_export_data_from_location', mock_read_export_data):
            with nt.assert_raises(Exception):
                result = self.view.read_export_data_and_check_schema(self.export_data, None)
                mock_read_export_data.assert_called_once()
                nt.assert_is_none(result)

    def test_read_export_data_and_check_schema_invalid_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_read_export_data = mock.MagicMock()
        mock_read_export_data.return_value = test_response
        mock_validate_file_json = mock.MagicMock()
        mock_validate_file_json.return_value = False
        with mock.patch.object(ExportData, 'read_export_data_from_location', mock_read_export_data):
            with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.validate_file_json', mock_validate_file_json):
                result = self.view.read_export_data_and_check_schema(self.export_data, None)
                mock_read_export_data.assert_called_once()
                mock_validate_file_json.assert_called_once()
                nt.assert_equal(result, False)

    # read_file_info_and_check_schema
    def test_read_file_info_and_check_schema_read_error(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_400_BAD_REQUEST
        test_response._content = json.dumps({}).encode('utf-8')

        mock_read_file_info = mock.MagicMock()
        mock_read_file_info.return_value = test_response
        with mock.patch.object(ExportData, 'read_file_info_from_location', mock_read_file_info):
            with nt.assert_raises(ProcessError):
                result = self.view.read_file_info_and_check_schema(ExportData(), {})
                nt.assert_is_none(result)

    def test_read_file_info_and_check_schema_read_exception(self):
        mock_read_file_info = mock.MagicMock()
        mock_read_file_info.side_effect = ValueError('Mock test fail to read file info')
        with mock.patch.object(ExportData, 'read_file_info_from_location', mock_read_file_info):
            with nt.assert_raises(ProcessError):
                result = self.view.read_file_info_and_check_schema(ExportData(), {})
                nt.assert_is_none(result)

    def test_read_file_info_and_check_schema_invalid_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_read_file_info = mock.MagicMock()
        mock_read_file_info.return_value = test_response
        mock_validate_file_json = mock.MagicMock()
        mock_validate_file_json.return_value = False
        with mock.patch.object(ExportData, 'read_file_info_from_location', mock_read_file_info):
            with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.validate_file_json', mock_validate_file_json):
                with nt.assert_raises(ProcessError):
                    result = self.view.read_file_info_and_check_schema(ExportData(), {})
                    nt.assert_is_none(result)

    def test_read_file_info_and_check_schema_valid_file(self):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        mock_read_file_info = mock.MagicMock()
        mock_read_file_info.return_value = test_response
        mock_validate_file_json = mock.MagicMock()
        mock_validate_file_json.return_value = True
        with mock.patch.object(ExportData, 'read_file_info_from_location', mock_read_file_info):
            with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.validate_file_json', mock_validate_file_json):
                result = self.view.read_file_info_and_check_schema(ExportData(), {})
                nt.assert_equal(result, {})

    # update_region_id
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_update_region_id(self, mock_check_progress):
        project = ProjectFactory()
        project._id = self.project_id
        project.add_addon('osfstorage', auth=AuthUserFactory())
        project.save()
        list_project_region_changed = self.view.update_region_id(None, 1, self.export_data_restore.destination, self.project_id, [])
        nt.assert_equal(list_project_region_changed, [project.id])
        mock_check_progress.assert_called()

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_update_region_id_project_not_found(self, mock_check_progress):
        list_project_region_changed = self.view.update_region_id(None, 1, self.export_data_restore.destination, None, [])
        nt.assert_equal(list_project_region_changed, [])
        mock_check_progress.assert_called()

    # recalculate_user_quota
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.update_user_used_quota')
    def test_recalculate_user_quota(self, mock_update_user_used_quota):
        inst = InstitutionFactory(_id=self.export_data_restore.destination._id)
        new_user = AuthUserFactory()
        new_user.affiliated_institutions.add(inst)
        self.view.recalculate_user_quota(self.export_data_restore.destination)
        mock_update_user_used_quota.assert_called()

    # create_folder_in_destination
    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.create_folder_path')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_create_folder_in_destination(self, mock_check_progress, mock_create_folder):
        export_data_folder = \
            [
                {
                    'path': '/630de9f5b71d8f06d918fbd7/',
                    'materialized_path': '/folder/',
                    'project': {
                        'id': 'pmockt',
                        'name': 'Project Mock'
                    }
                }
            ]

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_check_progress.return_value = None
        mock_create_folder.return_value = None
        result = self.view.create_folder_in_destination(
            task, 1,
            export_data_folder, self.addon_data_restore,
            None)
        mock_check_progress.assert_called()
        mock_create_folder.assert_called()
        nt.assert_equal(result, [])

    # copy_files_from_export_data_to_destination
    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.BaseFileNode.objects')
    def test_copy_files_from_export_data_to_destination_addon_storage(self, mock_basefilenode, mock_check_progress, mock_copy):
        addon_export_file = self.test_export_data_files
        addon_export_file[0]['path'] = '/@ember-decorators/utils/collapse-proto.d.ts'
        addon_export_file[0]['provider'] = 'nextcloudinstitutions'

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = True
        mock_check_progress.return_value = None
        mock_copy.return_value = {
            'data': {
                'id': 'nextcloudinstitutions/fake_id'
            }
        }
        basefilenode = BaseFileNodeFactory.create(id=11, _id='11', type='osf.nextcloudinstitutionsfile',
                                                  provider='nextcloudinstitutions',
                                                  _path='/61215649851ebb71d8f1ae01f4c99',
                                                  path='/61215649851ebb71d8f1ae01f4c99',
                                                  _materialized_path='/test.txt',
                                                  target_content_type_id=59)
        mock_file = mock.MagicMock()
        mock_basefilenode.filter.return_value = mock_file
        mock_file.exists.return_value = True
        mock_file.first.return_value = basefilenode

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                addon_export_file,
                self.addon_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_called()
            nt.assert_equal(result[0], [])

    @mock.patch('osf.models.BaseFileNode')
    @mock.patch('osf.models.BaseFileNode.objects')
    @mock.patch('osf.models.FileVersion.objects')
    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_osfstorage(self, mock_check_progress,
                                                                   mock_copy,
                                                                   mock_file_version, mock_file_node,
                                                                   mock_base_file_node):
        def create_node(*args, **kwargs):
            OsfStorageFileFactory.create(_id='fake_id')
            return {
                'data': {
                    'id': 'osfstorage/fake_id'
                }
            }

        bulkmount_export_files = self.test_export_data_files

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        user = AuthUserFactory.create(username='fake_user')
        file_version = FileVersionFactory.create(creator=user, identifier='1')
        mock_base_file_node.get_version.return_value = file_version
        mock_file_node.filter.return_value.update.return_value = {}
        mock_file_version.filter.return_value.update.return_value = {}

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.side_effect = create_node

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                bulkmount_export_files,
                self.bulk_mount_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_called()
            nt.assert_equal(len(result), 2)
            nt.assert_equal(result[0][0].get('file_tags'), ['hello', 'world'])
            nt.assert_equal(result[0][0].get('file_timestamp'), {})
            nt.assert_equal(result[0][0].get('project_id'), 'pmockt')

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_osfstorage_not_add_new_version(self, mock_check_progress,
                                                                                       mock_copy):
        def create_node(*args, **kwargs):
            file = OsfStorageFileFactory.create(_id='fake_id')
            user = AuthUserFactory.create(username='fake_user')
            version_1 = FileVersionFactory(creator=user, identifier='1')
            FileVersion.objects.filter(id=version_1.id).update(created='2023-04-18 04:40:25', modified='2023-04-18 04:40:25')
            file.add_version(version_1)
            file.add_version(FileVersionFactory(creator=user, identifier='2'))
            return {
                'data': {
                    'id': 'osfstorage/fake_id',
                    'attributes': {
                        'extra': {
                            'version': '2'
                        }
                    }
                }
            }

        bulkmount_export_files = self.test_export_data_files

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.side_effect = create_node

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                bulkmount_export_files,
                self.bulk_mount_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_called()
            nt.assert_equal(len(result), 2)
            nt.assert_equal(len(result[0][0].get('node').versions.all()), 1)
            nt.assert_equal(result[0][0].get('file_tags'), ['hello', 'world'])
            nt.assert_equal(result[0][0].get('file_timestamp'), {})
            nt.assert_equal(result[0][0].get('project_id'), 'pmockt')

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_other_bulk_mount_storage(self, mock_check_progress, mock_copy):
        bulkmount_export_files = self.test_export_data_files
        bulkmount_export_files[0]['provider'] = 'box'
        other_bulk_mount_data_restore = self.bulk_mount_data_restore
        other_bulk_mount_data_restore.destination.waterbutler_settings = {
            'storage': {
                'provider': 'box',
            }
        }

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.return_value = {
            'data': {
                'id': 'box/fake_id'
            }
        }

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                bulkmount_export_files,
                other_bulk_mount_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_called()
            nt.assert_equal(result[0], [])

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_empty_file_info_list(self, mock_check_progress, mock_copy):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.return_value = {
            'data': {
                'id': 'osfstorage/fake_id'
            }
        }

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                [], self.export_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_not_called()
            mock_copy.assert_not_called()
            nt.assert_equal(result[0], [])

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_empty_version(self, mock_check_progress, mock_copy):
        bulkmount_export_files = self.test_export_data_files
        bulkmount_export_files[0]['version'] = []

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.return_value = {
            'data': {
                'id': 'osfstorage/fake_id'
            }
        }

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                bulkmount_export_files,
                self.export_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_not_called()
            nt.assert_equal(result[0], [])

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_no_file_hash(self, mock_check_progress, mock_copy):
        bulkmount_export_files = self.test_export_data_files
        bulkmount_export_files[0]['version'] = [{
            'identifier': '',
            'metadata': {
                'kind': 'file',
            },
            'location': {}
        }]

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.return_value = {
            'data': {
                'id': 'osfstorage/fake_id'
            }
        }

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                bulkmount_export_files,
                self.export_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_not_called()
            nt.assert_equal(result[0], [])

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_copy_error(self, mock_check_progress, mock_copy):
        bulkmount_export_files = self.test_export_data_files

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.return_value = None

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                bulkmount_export_files,
                self.addon_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_called()
            nt.assert_equal(result[0], [])

    @mock.patch(f'{EXPORT_DATA_UTIL_PATH}.copy_file_from_location_to_destination')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_copy_files_from_export_data_to_destination_exception(self, mock_check_progress, mock_copy):
        bulkmount_export_files = self.test_export_data_files

        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        test_response._content = json.dumps({}).encode('utf-8')

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_is_add_on = mock.MagicMock()
        mock_is_add_on.return_value = False
        mock_check_progress.return_value = None
        mock_copy.side_effect = Exception('Mock test exception while downloading file from export data')

        with mock.patch(f'{EXPORT_DATA_UTIL_PATH}.is_add_on_storage', mock_is_add_on):
            result = self.view.copy_files_from_export_data_to_destination(
                task, 1,
                bulkmount_export_files,
                self.addon_data_restore,
                [], None)
            mock_is_add_on.assert_called()
            mock_check_progress.assert_called()
            mock_copy.assert_called()
            nt.assert_equal(result[0], [])

    def test_copy_files_from_export_data_to_destination_aborted(self):
        bulkmount_export_files = self.test_export_data_files

        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_check_progress = mock.MagicMock()
        mock_check_progress.side_effect = ProcessError('Mock test abort process while copy file to destination storage')
        with mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped', mock_check_progress):
            with nt.assert_raises(ProcessError):
                result = self.view.copy_files_from_export_data_to_destination(
                    task, 1,
                    bulkmount_export_files,
                    self.export_data_restore,
                    [], None)
                nt.assert_equal(result, None)

    # add_tag_and_timestamp_to_database
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_timestamp_to_file_node')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_tags_to_file_node')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_add_tag_and_timestamp_to_database(self, mock_check_process, mock_add_tags, mock_add_timestamp):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID
        list_file_nodes = [
            {
                'node': 1,
                'file_tags': ['tag1', 'tag2'],
                'file_timestamp': {},
                'project_id': self.project_id
            },
            {
                'node': 2,
                'file_tags': ['tag1'],
                'file_timestamp': {},
                'project_id': self.project_id
            }
        ]

        mock_check_process.return_value = None
        mock_add_tags.return_value = None
        mock_add_timestamp.return_value = None

        self.view.add_tag_and_timestamp_to_database(task, 1, list_file_nodes)
        nt.assert_equal(mock_check_process.call_count, 3)
        nt.assert_equal(mock_add_tags.call_count, 2)
        nt.assert_equal(mock_add_timestamp.call_count, 2)

    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_timestamp_to_file_node')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.add_tags_to_file_node')
    @mock.patch(f'{RESTORE_EXPORT_DATA_PATH}.check_if_restore_process_stopped')
    def test_add_tag_and_timestamp_to_database_empty_nodes(self, mock_check_process, mock_add_tags, mock_add_timestamp):
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID

        mock_check_process.return_value = None
        mock_add_tags.return_value = None
        mock_add_timestamp.return_value = None

        self.view.add_tag_and_timestamp_to_database(task, 1, [])
        mock_check_process.assert_called_once()
        mock_add_tags.assert_not_called()
        mock_add_timestamp.assert_not_called()


# Test cases for StopRestoreDataActionView
@pytest.mark.feature_202210
class TestStopRestoreDataActionView(AdminTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.export_data_restore = ExportDataRestoreFactory.create(task_id=FAKE_TASK_ID,
                                                                  status=ExportData.STATUS_RUNNING)
        cls.task = AbortableTask()
        cls.task.request_stack = LocalStack()
        cls.task.request.id = FAKE_TASK_ID
        cls.task.update_state(state=states.PENDING, meta={'current_restore_step': 1})
        cls.new_task_id = '00000000-0000-0000-0000-000000000001'
        cls.new_task = AbortableAsyncResult(cls.new_task_id)
        cls.view = restore.StopRestoreDataActionView()
        cls.view.kwargs = {
            'export_id': cls.export_data_restore.export.id,
        }

        cls.institution01 = InstitutionFactory(name='inst01')
        cls.institution02 = InstitutionFactory(name='inst02')
        cls.region_inst_01 = RegionFactory(_id=cls.institution01._id)
        cls.region_inst_02 = RegionFactory(_id=cls.institution02._id)
        cls.export_data_01 = ExportDataFactory(source=cls.region_inst_01)
        cls.export_data_02 = ExportDataFactory(source=cls.region_inst_02)
        cls.restore_data_01 = ExportDataRestoreFactory(export=cls.export_data_01)
        cls.restore_data_01.task_id = FAKE_TASK_ID + str(cls.restore_data_01.id)
        cls.restore_data_01.save()
        cls.restore_data_02 = ExportDataRestoreFactory(export=cls.export_data_02)
        cls.restore_data_02.task_id = FAKE_TASK_ID + str(cls.restore_data_02.id)
        cls.restore_data_02.save()

        cls.anon = AnonymousUser()

        cls.normal_user = AuthUserFactory(fullname='normal_user')
        cls.normal_user.is_staff = False
        cls.normal_user.is_superuser = False

        cls.superuser = AuthUserFactory(fullname='superuser')
        cls.superuser.is_staff = True
        cls.superuser.is_superuser = True
        cls.superuser.save()

        cls.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        cls.institution01_admin.is_staff = True
        cls.institution01_admin.affiliated_institutions.add(cls.institution01)
        cls.institution01_admin.save()

        cls.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        cls.institution02_admin.is_staff = True
        cls.institution02_admin.affiliated_institutions.add(cls.institution02)
        cls.institution02_admin.save()

    def setUp(self):
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })

    def test_init(self):
        nt.assert_equal(self.view.kwargs.get('export_id'), self.export_data_restore.export.id)
        nt.assert_is_not_none(self.view.post)

    def test_post_missing_params(self):
        request = APIRequestFactory().post('stop_restore_export_data', {})
        request.user = AuthUserFactory()
        self.view.request = request
        response = self.view.dispatch(request)
        nt.assert_equal(response.data, {'message': f'Missing required parameters.'})
        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post(self):
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': FAKE_TASK_ID,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = AuthUserFactory()

        self.view.export_data_restore = self.export_data_restore
        self.view.export_id = self.export_data_restore.export.id
        self.view.task_id = FAKE_TASK_ID
        response = self.view.post(request)
        nt.assert_equal(response.data, {'message': 'Stop restore data successfully.'})
        nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_post_restore_data_not_found(self):
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.new_task_id,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = AuthUserFactory()

        self.view.request = request
        response = self.view.dispatch(request, export_id=self.export_data_restore.export.id)
        nt.assert_equal(response.data, {'message': f'The restore export data is not exist'})
        nt.assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_post_task_no_result(self):
        self.task.update_state(state=states.PENDING, meta=None)

        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': FAKE_TASK_ID,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = AuthUserFactory()

        self.view.export_data_restore = self.export_data_restore
        self.view.export_id = self.export_data_restore.export.id
        self.view.task_id = FAKE_TASK_ID
        response = self.view.post(request)
        nt.assert_equal(response.data, {'message': f'Stop restore data successfully.'})
        nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_post_task_is_not_running(self):
        self.task.update_state(state=states.SUCCESS, meta={'message': 'Restore data successfully.'})
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': FAKE_TASK_ID,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = AuthUserFactory()

        self.view.export_data_restore = self.export_data_restore
        self.view.export_id = self.export_data_restore.export.id
        self.view.task_id = FAKE_TASK_ID
        response = self.view.post(request)
        nt.assert_equal(response.data, {'message': f'Stop restore data successfully.'})
        nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test_post_task_done_moving_files(self):
        self.task.update_state(state=states.PENDING, meta={'current_restore_step': 4})
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': FAKE_TASK_ID,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = AuthUserFactory()

        self.view.export_data_restore = self.export_data_restore
        self.view.export_id = self.export_data_restore.export.id
        self.view.task_id = FAKE_TASK_ID
        response = self.view.post(request)
        nt.assert_equal(response.data, {'message': f'Cannot stop restore process at this time.'})
        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch.object(AbortableAsyncResult, 'abort')
    def test_post_task_cannot_abort(self, mock_task_abort):
        self.task.update_state(state=states.PENDING, meta={'current_restore_step': 1})
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': FAKE_TASK_ID,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = AuthUserFactory()

        self.view.export_data_restore = self.export_data_restore
        self.view.export_id = self.export_data_restore.export.id
        self.view.task_id = FAKE_TASK_ID
        response = self.view.post(request)
        mock_task_abort.assert_called()
        nt.assert_equal(response.data, {'message': f'Cannot stop restore process at this time.'})
        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test__test_func__anonymous(self):
        view = restore.StopRestoreDataActionView()
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': FAKE_TASK_ID,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = self.anon
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__normal_user(self):
        view = restore.StopRestoreDataActionView()
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': FAKE_TASK_ID,
            'destination_id': self.export_data_restore.destination.id,
        })
        request.user = self.normal_user
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__super(self):
        view = restore.StopRestoreDataActionView()
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_01.task_id,
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_01.id
        view.destination_inst_id = self.institution01.id
        view.export_id = self.export_data_01.id
        view.export_data_inst_id = self.institution01.id
        view.export_data_restore = self.restore_data_01
        view.export_data_restore_inst_id = self.institution01.id
        nt.assert_equal(view.test_func(), True)

    def test__test_func__addmin_with_permission(self):
        view = restore.StopRestoreDataActionView()
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_01.task_id,
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_01.id
        view.destination_inst_id = self.institution01.id
        view.export_id = self.export_data_01.id
        view.export_data_inst_id = self.institution01.id
        view.export_data_restore = self.restore_data_01
        view.export_data_restore_inst_id = self.institution01.id
        nt.assert_equal(view.test_func(), True)

    def test__test_func__addmin_without_permission(self):
        view = restore.StopRestoreDataActionView()

        # not same institution of login user
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_01.task_id,
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.institution02_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_01.id
        view.destination_inst_id = self.institution01.id
        view.export_id = self.export_data_01.id
        view.export_data_inst_id = self.institution01.id
        view.export_data_restore = self.restore_data_01
        view.export_data_restore_inst_id = self.institution01.id
        nt.assert_equal(view.test_func(), False)

        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_02.task_id,
            'destination_id': self.restore_data_01.destination.id,
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.destination_id = self.region_inst_01.id
        view.destination_inst_id = self.institution01.id
        view.export_id = self.export_data_02.id
        view.export_data_inst_id = self.institution02.id
        view.export_data_restore = self.restore_data_02
        view.export_data_restore_inst_id = self.institution02.id
        nt.assert_equal(view.test_func(), False)

        # admin not in institution
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_02.task_id,
            'destination_id': self.restore_data_02.destination.id,
        })
        self.institution02_admin.affiliated_institutions = []
        request.user = self.institution02_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.destination_id = self.region_inst_02.id
        view.destination_inst_id = self.institution02.id
        view.export_id = self.export_data_02.id
        view.export_data_inst_id = self.institution02.id
        view.export_data_restore = self.restore_data_02
        view.export_data_restore_inst_id = self.institution02.id
        nt.assert_equal(view.test_func(), False)

    def test__test_func__super_with_param_not_same_inst(self):
        view = restore.StopRestoreDataActionView()
        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_01.task_id,
            'destination_id': self.region_inst_02.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.destination_id = self.region_inst_02.id
        view.destination_inst_id = self.institution02.id
        view.export_id = self.export_data_02.id
        view.export_data_inst_id = self.institution02.id
        view.export_data_restore = self.restore_data_01
        view.export_data_restore_inst_id = self.institution01.id
        nt.assert_equal(view.test_func(), False)

        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_01.task_id,
            'destination_id': self.region_inst_02.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.destination_id = self.region_inst_02.id
        view.destination_inst_id = self.institution02.id
        view.export_id = self.export_data_01.id
        view.export_data_inst_id = self.institution01.id
        view.export_data_restore = self.restore_data_01
        view.export_data_restore_inst_id = self.institution01.id
        nt.assert_equal(view.test_func(), False)

        request = APIRequestFactory().post('stop_restore_export_data', {
            'task_id': self.restore_data_01.task_id,
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.destination_id = self.region_inst_01.id
        view.destination_inst_id = self.institution01.id
        view.export_id = self.export_data_02.id
        view.export_data_inst_id = self.institution02.id
        view.export_data_restore = self.restore_data_01
        view.export_data_restore_inst_id = self.institution01.id
        nt.assert_equal(view.test_func(), False)


# Test cases for CheckRunningRestoreActionView
@pytest.mark.feature_202210
class TestCheckRunningRestoreActionView(AdminTestCase):

    @classmethod
    def setUpTestData(cls):
        cls.export_data_restore = ExportDataRestoreFactory.create(task_id=FAKE_TASK_ID,
                                                                  status=ExportData.STATUS_RUNNING)
        cls.institution01 = InstitutionFactory(name='inst01')
        cls.institution02 = InstitutionFactory(name='inst02')
        cls.region_inst_01 = RegionFactory(_id=cls.institution01._id)
        cls.region_inst_02 = RegionFactory(_id=cls.institution02._id)
        cls.export_data_01 = ExportDataFactory(source=cls.region_inst_01)
        cls.export_data_02 = ExportDataFactory(source=cls.region_inst_02)
        cls.restore_data_01 = ExportDataRestoreFactory(export=cls.export_data_01)
        cls.restore_data_01.task_id = FAKE_TASK_ID + str(cls.restore_data_01.id)
        cls.restore_data_01.save()
        cls.restore_data_02 = ExportDataRestoreFactory(export=cls.export_data_02)
        cls.restore_data_02.task_id = FAKE_TASK_ID + str(cls.restore_data_02.id)
        cls.restore_data_02.save()

        cls.anon = AnonymousUser()

        cls.normal_user = AuthUserFactory(fullname='normal_user')
        cls.normal_user.is_staff = False
        cls.normal_user.is_superuser = False

        cls.superuser = AuthUserFactory(fullname='superuser')
        cls.superuser.is_staff = True
        cls.superuser.is_superuser = True
        cls.superuser.save()

        cls.institution01_admin = AuthUserFactory(fullname='admin001_inst01')
        cls.institution01_admin.is_staff = True
        cls.institution01_admin.affiliated_institutions.add(cls.institution01)
        cls.institution01_admin.save()

        cls.institution02_admin = AuthUserFactory(fullname='admin001_inst02')
        cls.institution02_admin.is_staff = True
        cls.institution02_admin.affiliated_institutions.add(cls.institution02)
        cls.institution02_admin.save()

    def setUp(self):
        self.view = restore.CheckRunningRestoreActionView()

    def test_init(self):
        nt.assert_is_not_none(self.view.get)

    def test_get_success(self):
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.export_data_restore.destination.id,
        })
        self.view.destination_id = self.export_data_restore.destination.id
        response = self.view.get(request)
        nt.assert_equal(response.data, {
            'task_id': FAKE_TASK_ID,
        })
        nt.assert_equal(response.status_code, status.HTTP_200_OK)

    def test__test_func__anonymous(self):
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.anon
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__normal_user(self):
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.normal_user
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), False)

    def test__test_func__super(self):
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), True)

    def test__test_func__addmin_with_permission(self):
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), True)

    def test__test_func__addmin_without_permission(self):
        #not same institution of login user
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.institution02_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        view.export_data = self.export_data_01
        view.destination_id = self.region_inst_01.id
        nt.assert_equal(view.test_func(), False)

        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_02.id,
        })
        request.user = self.institution01_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.export_data = self.export_data_02
        view.destination_id = self.region_inst_02.id
        nt.assert_equal(view.test_func(), False)

        # admin not in institution
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_02.id,
        })
        self.institution02_admin.affiliated_institutions = []
        request.user = self.institution02_admin
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.export_data = self.export_data_02
        view.destination_id = self.region_inst_02.id
        nt.assert_equal(view.test_func(), False)

    def test__test_func__without_param(self):
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {})
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_01.id,
        }
        nt.assert_equal(view.test_func(), True)

    def test__test_func__super_with_param_not_same_inst(self):
        view = restore.CheckRunningRestoreActionView()
        request = APIRequestFactory().get('check_running_restore', {
            'destination_id': self.region_inst_01.id,
        })
        request.user = self.superuser
        view.request = request
        view.kwargs = {
            'export_id': self.export_data_02.id,
        }
        view.export_data = self.export_data_02
        view.destination_id = self.region_inst_01.id
        nt.assert_equal(view.test_func(), False)
