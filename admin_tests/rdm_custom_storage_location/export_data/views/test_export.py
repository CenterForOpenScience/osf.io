import mock
import pytest
import unittest
import requests
from celery import states
from celery.contrib.abortable import AbortableAsyncResult, AbortableTask
from celery.utils.threads import LocalStack
from django.db import IntegrityError
from django.http import JsonResponse
from django.test import RequestFactory
from nose import tools as nt
from rest_framework import status

from admin.rdm_custom_storage_location.export_data.views import export
from framework.celery_tasks import app as celery_app
from osf.models import ExportData
from osf_tests.factories import (
    InstitutionFactory,
    ExportDataLocationFactory,
    AuthUserFactory,
    RegionFactory,
    ExportDataFactory, ProjectFactory,
)
from tests.base import AdminTestCase

FAKE_TASK_ID = '00000000-0000-0000-0000-000000000000'
EXPORT_DATA_PATH = 'admin.rdm_custom_storage_location.export_data.views.export'
EXPORT_DATA_TASK_PATH = 'admin.rdm_custom_storage_location.tasks'
FAKE_EXPORT_DATA_JSON = {
    'institution': {
        'id': 66,
        'guid': 'wustl',
        'name': 'Washington University in St. Louis [Test]'
    },
    'process_start': '2023-05-09 09:14:44',
    'process_end': '2023-05-09 09:25:18',
    'storage': {
        'name': 'United States',
        'type': 'NII Storage'
    },
    'projects_numb': 1,
    'files_numb': 3,
    'size': 1470,
    'file_path': '/export_66_1683623684/file_info_wustl_1683623684.json'
}


class TestGetTaskResult(unittest.TestCase):
    def test_dict_input(self):
        result = {'key': 'value'}
        self.assertEqual(export.get_task_result(result), result)

    def test_string_input(self):
        result = 'Error occurred'
        expected_result = {'message': result}
        self.assertEqual(export.get_task_result(result), expected_result)

    def test_exception_input(self):
        result = Exception('An exception occurred')
        expected_result = {'message': str(result)}
        self.assertEqual(export.get_task_result(result), expected_result)

    def test_other_input(self):
        result = 123  # A non-string, non-dict input
        expected_result = {}
        self.assertEqual(export.get_task_result(result), expected_result)


class FakeTask:
    def __init__(self, state, result, check_abort=True):
        self.task_id = 100
        self.state = state
        self.result = result
        self.check_abort = check_abort

    def is_aborted(self):
        return self.check_abort


@unittest.skip('to check travis-ci and update test-cases')
class TestExportDataProcess(unittest.TestCase):
    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_export_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__export_data_model_success(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min, mock_upload_export_data_file):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED
        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.return_value = []
        mock_upload_file_info_file = mock.MagicMock()
        mock_upload_file_info_file.return_value = created_response
        mock_upload_export_data_file.return_value = created_response

        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_file', mock_upload_file_info_file):
            result = export.export_data_process(fake_task, None, export_data.pk)
            mock_extract_json.assert_called()
            mock_create_export_data_folder.assert_called()
            mock_create_export_data_files_folder.assert_called()
            mock_get_source_file_versions_min.assert_called()
            mock_upload_file_info_file.assert_called()
            mock_upload_export_data_file.assert_called()
            nt.assert_is_not_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__aborted_before_create_export_data_folder(
            self, mock_extract_json):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=True)

        mock_extract_json.return_value = {}, {}

        result = export.export_data_process(fake_task, None, export_data.pk)
        mock_extract_json.assert_called()
        nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__aborted_before_create_export_data_folder_raise_exception(
            self, mock_extract_json):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=True)

        mock_extract_json.side_effect = Exception('mock error')

        with pytest.raises(Exception):
            export.export_data_process(fake_task, None, export_data.pk)
            mock_extract_json.assert_called()

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__create_export_data_folder_error(
            self, mock_extract_json, mock_create_export_data_folder):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)
        error_response = requests.Response()
        error_response.status_code = status.HTTP_400_BAD_REQUEST

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = error_response
        mock_rollback_export_data = mock.MagicMock()
        mock_rollback_export_data.return_value = None

        with mock.patch(f'{EXPORT_DATA_PATH}.export_data_rollback_process', mock_rollback_export_data):
            result = export.export_data_process(fake_task, None, export_data.pk)
            mock_extract_json.assert_called()
            mock_create_export_data_folder.assert_called()
            mock_rollback_export_data.assert_called()
            nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__aborted_before_create_export_data_files_folder(
            self, mock_extract_json, mock_create_export_data_folder):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        def update_fake_task(*args, **kwargs):
            nonlocal fake_task
            fake_task.check_abort = True
            created_response = requests.Response()
            created_response.status_code = status.HTTP_201_CREATED
            return created_response

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.side_effect = update_fake_task

        result = export.export_data_process(fake_task, None, export_data.pk)
        mock_extract_json.assert_called()
        mock_create_export_data_folder.assert_called()
        nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__create_export_data_files_folder_error(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED
        error_response = requests.Response()
        error_response.status_code = status.HTTP_400_BAD_REQUEST

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = error_response
        mock_rollback_export_data = mock.MagicMock()
        mock_rollback_export_data.return_value = None

        with mock.patch(f'{EXPORT_DATA_PATH}.export_data_rollback_process', mock_rollback_export_data):
            result = export.export_data_process(fake_task, None, export_data.pk)
            mock_extract_json.assert_called()
            mock_create_export_data_folder.assert_called()
            mock_create_export_data_files_folder.assert_called()
            mock_rollback_export_data.assert_called()
            nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__aborted_before_get_source_file_version_min(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED

        def update_fake_task(*args, **kwargs):
            nonlocal fake_task
            fake_task.check_abort = True
            return created_response

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.side_effect = update_fake_task

        result = export.export_data_process(fake_task, None, export_data.pk)
        mock_extract_json.assert_called()
        mock_create_export_data_folder.assert_called()
        mock_create_export_data_files_folder.assert_called()
        nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__aborted_before_copy_export_data_file_to_location(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED

        def update_fake_task(*args, **kwargs):
            nonlocal fake_task
            fake_task.check_abort = True
            return [(None, None, None, None, None, None)]

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.side_effect = update_fake_task

        result = export.export_data_process(fake_task, None, export_data.pk)
        mock_extract_json.assert_called()
        mock_create_export_data_folder.assert_called()
        mock_create_export_data_files_folder.assert_called()
        mock_get_source_file_versions_min.assert_called()
        nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_export_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__copy_export_data_file_to_location_error(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min, mock_upload_export_data_file):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED
        error_response = requests.Response()
        error_response.status_code = status.HTTP_400_BAD_REQUEST

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.return_value = [(None, None, None, None, None, None)]
        mock_copy_export_data_file_to_location = mock.MagicMock()
        mock_copy_export_data_file_to_location.return_value = error_response
        mock_rollback_export_data = mock.MagicMock()
        mock_rollback_export_data.return_value = None
        mock_upload_export_data_file.return_value = created_response

        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.copy_export_data_file_to_location',
                        mock_copy_export_data_file_to_location):
            with mock.patch(f'{EXPORT_DATA_PATH}.export_data_rollback_process', mock_rollback_export_data):
                result = export.export_data_process(fake_task, None, export_data.pk)
                mock_extract_json.assert_called()
                mock_create_export_data_folder.assert_called()
                mock_create_export_data_files_folder.assert_called()
                mock_get_source_file_versions_min.assert_called()
                mock_copy_export_data_file_to_location.assert_called()
                mock_rollback_export_data.assert_not_called()
                mock_upload_export_data_file.assert_called()
                nt.assert_is_not_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_export_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__copy_export_data_file_to_location_201(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min, mock_upload_export_data_file):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.return_value = [(None, None, None, None, 'duplicate', None),
                                                          (None, None, None, None, 'duplicate', None)]
        mock_copy_export_data_file_to_location = mock.MagicMock()
        mock_copy_export_data_file_to_location.return_value = created_response
        mock_rollback_export_data = mock.MagicMock()
        mock_rollback_export_data.return_value = None
        mock_upload_export_data_file.return_value = created_response
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.copy_export_data_file_to_location',
                        mock_copy_export_data_file_to_location):
            with mock.patch(f'{EXPORT_DATA_PATH}.export_data_rollback_process', mock_rollback_export_data):
                result = export.export_data_process(fake_task, None, export_data.pk)
                mock_extract_json.assert_called()
                mock_create_export_data_folder.assert_called()
                mock_create_export_data_files_folder.assert_called()
                mock_get_source_file_versions_min.assert_called()
                mock_copy_export_data_file_to_location.assert_called()
                mock_rollback_export_data.assert_not_called()
                mock_upload_export_data_file.assert_called()
                nt.assert_is_not_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__abort_before_upload_file_info_file(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED

        def update_fake_task(*args, **kwargs):
            nonlocal fake_task
            fake_task.check_abort = True
            return []

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.side_effect = update_fake_task

        result = export.export_data_process(fake_task, None, export_data.pk)
        mock_extract_json.assert_called()
        mock_create_export_data_folder.assert_called()
        mock_create_export_data_files_folder.assert_called()
        mock_get_source_file_versions_min.assert_called()
        nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__upload_file_info_file_error(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED
        error_response = requests.Response()
        error_response.status_code = status.HTTP_400_BAD_REQUEST

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.return_value = []
        mock_upload_file_info_file = mock.MagicMock()
        mock_upload_file_info_file.return_value = error_response
        mock_rollback_export_data = mock.MagicMock()
        mock_rollback_export_data.return_value = None

        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_file', mock_upload_file_info_file):
            with mock.patch(f'{EXPORT_DATA_PATH}.export_data_rollback_process', mock_rollback_export_data):
                result = export.export_data_process(fake_task, None, export_data.pk)
                mock_extract_json.assert_called()
                mock_create_export_data_folder.assert_called()
                mock_create_export_data_files_folder.assert_called()
                mock_get_source_file_versions_min.assert_called()
                mock_upload_file_info_file.assert_called()
                mock_rollback_export_data.assert_called()
                nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__aborted_before_upload_export_data_file(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)

        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED

        def update_fake_task(*args, **kwargs):
            nonlocal fake_task
            fake_task.check_abort = True
            return created_response

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.return_value = []
        mock_upload_file_info_file = mock.MagicMock()
        mock_upload_file_info_file.side_effect = update_fake_task

        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_file', mock_upload_file_info_file):
            result = export.export_data_process(fake_task, None, export_data.pk)
            mock_extract_json.assert_called()
            mock_create_export_data_folder.assert_called()
            mock_create_export_data_files_folder.assert_called()
            mock_get_source_file_versions_min.assert_called()
            mock_upload_file_info_file.assert_called()
            nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_export_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__upload_export_data_file_error(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min, mock_upload_export_data_file):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)
        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED
        error_response = requests.Response()
        error_response.status_code = status.HTTP_400_BAD_REQUEST

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.return_value = []
        mock_upload_file_info_file = mock.MagicMock()
        mock_upload_file_info_file.return_value = created_response
        mock_upload_export_data_file.return_value = error_response
        mock_rollback_export_data = mock.Mock()
        mock_rollback_export_data.return_value = None

        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_file', mock_upload_file_info_file):
            with mock.patch(f'{EXPORT_DATA_PATH}.export_data_rollback_process', mock_rollback_export_data):
                result = export.export_data_process(fake_task, None, export_data.pk)
                mock_extract_json.assert_called()
                mock_create_export_data_folder.assert_called()
                mock_create_export_data_files_folder.assert_called()
                mock_get_source_file_versions_min.assert_called()
                mock_upload_file_info_file.assert_called()
                mock_upload_export_data_file.assert_called()
                mock_rollback_export_data.assert_called()
                nt.assert_is_none(result)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_export_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    def test_export_data_process__aborted_before_check_export_data_status(
            self, mock_extract_json, mock_create_export_data_folder, mock_create_export_data_files_folder,
            mock_get_source_file_versions_min, mock_upload_export_data_file):
        export_data = ExportDataFactory()
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)
        created_response = requests.Response()
        created_response.status_code = status.HTTP_201_CREATED

        def update_fake_task(*args, **kwargs):
            nonlocal fake_task
            fake_task.check_abort = True
            return created_response

        mock_extract_json.return_value = {}, {}
        mock_create_export_data_folder.return_value = created_response
        mock_create_export_data_files_folder.return_value = created_response
        mock_get_source_file_versions_min.return_value = []
        mock_upload_file_info_file = mock.MagicMock()
        mock_upload_file_info_file.return_value = created_response
        mock_upload_export_data_file.side_effect = update_fake_task

        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_file', mock_upload_file_info_file):
            result = export.export_data_process(fake_task, None, export_data.pk)
            mock_extract_json.assert_called()
            mock_create_export_data_folder.assert_called()
            mock_create_export_data_files_folder.assert_called()
            mock_get_source_file_versions_min.assert_called()
            mock_upload_file_info_file.assert_called()
            mock_upload_export_data_file.assert_called()
            nt.assert_is_none(result)


@unittest.skip('to check travis-ci and update test-cases')
class TestExportDataRollbackProcess(unittest.TestCase):
    @pytest.mark.django_db
    def test_export_data_rollback_process__success(self):
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)
        cookies = 'abcd'
        mock_os = mock.MagicMock()
        mock_os.return_value = True
        mock_request = mock.MagicMock()
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=400)
        mock_obj = mock.MagicMock()
        export_data = ExportDataFactory()
        mock_obj.filter.return_value.exists.return_value = export_data
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
            with mock.patch(f'{EXPORT_DATA_PATH}.os.remove', mock_obj):
                export.export_data_rollback_process(fake_task, cookies, export_data.id)
                mock_obj.assert_called()

    @pytest.mark.django_db
    def test_export_data_rollback_process__status_running(self):
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)
        cookies = 'abcd'
        export_data = ExportDataFactory()
        export_data.status = ExportData.STATUS_RUNNING
        mock_os = mock.MagicMock()
        mock_os.return_value = True
        mock_request = mock.MagicMock()
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=400)
        mock_obj = mock.MagicMock()
        mock_obj.filter.return_value.first.return_value = export_data
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
            with mock.patch(f'{EXPORT_DATA_PATH}.os.remove', mock_obj):
                with mock.patch('osf.models.export_data.requests', mock_obj):
                    export.export_data_rollback_process(fake_task, cookies, export_data.id)

    @pytest.mark.django_db
    def test_export_data_rollback_process__raise_exception(self):
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)
        cookies = 'abcd'
        export_data = ExportDataFactory()
        export_data.status = ExportData.STATUS_RUNNING
        mock_os = mock.MagicMock()
        mock_os.return_value = True
        mock_request = mock.MagicMock()
        mock_request.delete.side_effect = Exception('mock error')
        mock_obj = mock.MagicMock()
        mock_obj.filter.return_value.first.return_value = export_data
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
            with mock.patch(f'{EXPORT_DATA_PATH}.os.remove', mock_obj):
                with mock.patch('osf.models.export_data.requests', mock_request):
                    with pytest.raises(Exception):
                        export.export_data_rollback_process(fake_task, cookies, export_data.id)

    @pytest.mark.django_db
    def test_export_data_rollback_process__status_stopped(self):
        fake_task = FakeTask(states.SUCCESS, {}, check_abort=False)
        cookies = 'abcd'
        export_data = ExportDataFactory()
        export_data.status = ExportData.STATUS_STOPPED
        mock_obj = mock.MagicMock()
        mock_obj.filter.return_value.first.return_value = export_data
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
            res = export.export_data_rollback_process(fake_task, cookies, export_data.id)
            nt.assert_equal(res, None)


class TestExportDataBaseActionView(AdminTestCase):
    def setUp(self):
        super(TestExportDataBaseActionView, self).setUp()
        self.user = AuthUserFactory()
        self.institution = InstitutionFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_superuser = True
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.request = RequestFactory().get('/fake_path')
        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.location = ExportDataLocationFactory()
        self.request.user = self.user
        self.view = export.ExportDataBaseActionView()
        self.view.request = self.request

    def test_extract_input__not_institution_id(self):
        self.request.data = {
            'source_id': self.source.id,
            'location_id': self.location.id,
        }
        res = self.view.extract_input(self.request)
        nt.assert_equal(res.status_code, 400)
        nt.assert_equal(res.data['message'], 'Permission denied for this institution')

    def test_extract_input_not__source_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'location_id': self.location.id,
        }
        res = self.view.extract_input(self.request)
        nt.assert_equal(res.data['message'], 'Permission denied for this storage')
        nt.assert_equal(res.status_code, 400)

    def test_extract_input_not__location_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
        }
        res = self.view.extract_input(self.request)
        nt.assert_equal(res.data['message'], 'Permission denied for this export storage location')
        nt.assert_equal(res.status_code, 400)

    def test_extract_input__success(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }
        mock_institution = mock.MagicMock()
        mock_institution.get.return_value = self.institution
        mock_region = mock.MagicMock()
        mock_region.get.return_value = self.source
        mock_location = mock.MagicMock()
        mock_location.get.return_value = self.location
        with mock.patch(f'{EXPORT_DATA_PATH}.Institution.objects', mock_institution):
            with mock.patch(f'{EXPORT_DATA_PATH}.Region.objects', mock_region):
                with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataLocation.objects', mock_location):
                    institution, source_storage, location = self.view.extract_input(self.request)
                    nt.assert_equal(institution.id, self.institution.id)
                    nt.assert_equal(source_storage.id, self.source.id)
                    nt.assert_equal(location.id, self.location.id)


@unittest.skip('to check travis-ci and update test-cases')
class TestExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestExportDataActionView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.institution = InstitutionFactory()
        self.source = RegionFactory()
        self.location = ExportDataLocationFactory()
        self.view = export.ExportDataActionView()
        self.request.user = self.user
        self.export_data = ExportDataFactory()

    def test_post__success(self):
        self.request.COOKIES = 'abcd'
        mock_task = mock.MagicMock()
        fake_task = FakeTask('completed', 'OK')
        mock_task.return_value = fake_task
        mock_class = mock.MagicMock()
        mock_class.return_value = self.institution, self.source, self.location
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input', mock_class):
            with mock.patch(f'{EXPORT_DATA_TASK_PATH}.run_export_data_process.delay', mock_task):
                res = self.view.post(self.request)
                nt.assert_equal(res.status_code, 200)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input')
    def test_post__exception(self, mock_class):
        mock_class.return_value = self.institution, self.source, self.location
        self.request.COOKIES = 'abcd'
        with mock.patch('osf.models.ExportData.objects.create', side_effect=IntegrityError('mocked error')):
            res = self.view.post(self.request)
            nt.assert_equal(res.status_code, 400)


@unittest.skip('to check travis-ci and update test-cases')
class TestStopExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestStopExportDataActionView, self).setUp()
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })

        self.institution = InstitutionFactory()
        self.source_storage = RegionFactory()
        self.location = ExportDataLocationFactory()
        self.request = RequestFactory().post('export_data', {})
        self.request.user = AuthUserFactory()
        self.view = export.StopExportDataActionView()
        self.task_id = FAKE_TASK_ID
        self.mock_extract_data = mock.Mock()
        self.mock_extract_data.return_value = self.institution, self.source_storage, self.location

    def test_init(self):
        nt.assert_is_not_none(self.view.post)

    def test_post__no_task_id(self):
        self.request.data = {}
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input', self.mock_extract_data):
            response = self.view.post(self.request)
            expected_data = {
                'task_id': None,
                'message': f'Permission denied for this export process'
            }
            nt.assert_equal(response.data, expected_data)
            nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post__process_not_running(self):
        self.request.data = {
            'task_id': self.task_id,
        }
        ExportDataFactory.create(
            task_id=self.task_id,
            source=self.source_storage,
            location=self.location,
            status=ExportData.STATUS_PENDING
        )
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input', self.mock_extract_data):
            response = self.view.post(self.request)
            expected_data = {
                'task_id': self.task_id,
                'task_state': states.PENDING,
                'status': ExportData.STATUS_COMPLETED,
                'result': {},
                'message': f'Cannot stop this export process'
            }
            nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)
            nt.assert_equal(response.data, expected_data)

    def test_post__fail_to_abort(self):
        self.request.data = {
            'task_id': self.task_id,
        }
        ExportDataFactory.create(
            task_id=FAKE_TASK_ID,
            source=self.source_storage,
            location=self.location,
            status=ExportData.STATUS_RUNNING
        )
        mock_abort_task = mock.Mock()
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input', self.mock_extract_data):
            with mock.patch(f'{EXPORT_DATA_PATH}.AbortableAsyncResult.abort', mock_abort_task):
                response = self.view.post(self.request)
                expected_data = {
                    'task_id': self.task_id,
                    'task_state': states.PENDING,
                    'status': ExportData.STATUS_RUNNING,
                    'message': f'Cannot abort this export process'
                }
                nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)
                nt.assert_equal(response.data, expected_data)

    def test_post__success(self):
        self.request.data = {
            'task_id': self.task_id,
        }
        ExportDataFactory.create(
            task_id=FAKE_TASK_ID,
            source=self.source_storage,
            location=self.location,
            status=ExportData.STATUS_RUNNING
        )
        mock_rollback_process = mock.Mock()
        mock_rollback_process.return_value = AbortableAsyncResult(self.task_id)
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input', self.mock_extract_data):
            with mock.patch(f'{EXPORT_DATA_TASK_PATH}.run_export_data_rollback_process.delay', mock_rollback_process):
                response = self.view.post(self.request)
                nt.assert_equal(response.data, {
                    'task_id': self.task_id,
                    'task_state': 'ABORTED',
                    'result': {},
                    'status': ExportData.STATUS_RUNNING,
                })
                nt.assert_equal(response.status_code, status.HTTP_200_OK)


class TestCheckStateExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestCheckStateExportDataActionView, self).setUp()
        self.institution = InstitutionFactory()
        self.source = RegionFactory()
        self.location = ExportDataLocationFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = export.CheckStateExportDataActionView()
        self.view.request = self.request

    def test_post_success(self):
        self.request.data = {
            'task_id': 100,
        }
        mock_obj = mock.MagicMock()
        mock_class = mock.mock.MagicMock()
        mock_task = mock.MagicMock()
        fake_task = FakeTask('completed', 'OK')
        task = AbortableTask()
        task.request_stack = LocalStack()
        task.request.id = FAKE_TASK_ID
        mock_task.return_value = fake_task
        mock_obj.filter.return_value.exists.return_value = ExportDataFactory()
        mock_class.return_value = self.institution.id, self.source.id, self.location.id
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input', mock_class):
            with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
                with mock.patch(f'{EXPORT_DATA_PATH}.AbortableAsyncResult', mock_task):
                    response = self.view.post(self.request)
        nt.assert_equal(response.status_code, 200)

    def test_post_error(self):
        self.request.data = {
            'task_id': None,
        }
        mock_obj = mock.MagicMock()
        mock_class = mock.mock.MagicMock()
        mock_obj.filter.return_value.exists.return_value = ExportDataFactory()
        mock_class.return_value = self.institution.id, self.source.id, self.location.id
        with mock.patch(f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input', mock_class):
            with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
                response = self.view.post(self.request)
        nt.assert_equal(response.status_code, 400)


class TestCheckDataExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestCheckDataExportDataActionView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.institution = InstitutionFactory()
        self.source = RegionFactory()
        self.location = ExportDataLocationFactory()
        self.request.user = self.user
        self.view = export.CheckDataExportDataActionView()
        self.view.request = self.request

    def test_post(self):
        mock_obj = mock.MagicMock()
        mock_class = mock.mock.MagicMock()
        mock_obj.filter.return_value.exists.return_value = True
        mock_class.return_value = self.institution.id, self.source.id, self.location.id
        with mock.patch(
                f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input',
                mock_class):
            with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
                response = self.view.post(self.request)
        nt.assert_equal(response.status_code, 200)


class TestCheckRunningExportActionView(AdminTestCase):
    def setUp(self):
        super(TestCheckRunningExportActionView, self).setUp()
        self.user = AuthUserFactory()
        self.request = RequestFactory().get('/fake_path')
        self.institution = InstitutionFactory()
        self.source = RegionFactory()
        self.location = ExportDataLocationFactory()
        self.request.user = self.user
        self.view = export.CheckRunningExportActionView()
        self.view.request = self.request
        self.export_data = [ExportDataFactory()]

    def test_post(self):
        mock_obj = mock.MagicMock()
        mock_class = mock.mock.MagicMock()
        mock_obj.filter.return_value = self.export_data
        mock_class.return_value = self.institution.id, self.source.id, self.location.id
        with mock.patch(
                f'{EXPORT_DATA_PATH}.ExportDataBaseActionView.extract_input',
                mock_class):
            with mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects', mock_obj):
                response = self.view.post(self.request)
        nt.assert_equal(response.status_code, 200)
