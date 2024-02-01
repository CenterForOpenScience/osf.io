import json
import logging
import mock
import pytest
import time
import unittest
from celery import states
from celery.contrib.abortable import AbortableAsyncResult, AbortableTask, ABORTED
from celery.exceptions import Ignore
from celery.utils.threads import LocalStack
from django.db import IntegrityError
from django.test import RequestFactory
from django_celery_results.models import TaskResult
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
    ExportDataFactory,
)
from tests.base import AdminTestCase

logger = logging.getLogger(__name__)
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


class TestSeparateFailedFiles(unittest.TestCase):
    def setUp(self):
        self.files = [
            {
                'id': 3000,
                'path': '/24chars24chars24chars24c',
                'materialized_path': '/folder_path/file_name.ext',
                'name': 'file_name.ext',
                'provider': 'osfstorage',
                'project': {
                    'id': 'prjid',
                    'name': 'PRJ 20231005 001'
                },
                'tags': [],
                'version': [
                ],
                'size': 3000,
                'location': {
                    'object': '64chars64chars64chars64chars64chars64chars64chars64chars64chars6',
                    'provider': 's3compat'
                },
                'timestamp': {},
                'checkout_id': None
            },
            {
                'id': 4000,
                'path': '/24chars24chars24chars24c',
                'materialized_path': '/folder_path/file_name.ext',
                'name': 'file_name.ext',
                'provider': 'osfstorage',
                'project': {
                    'id': 'prjid',
                    'name': 'PRJ 20231005 001'
                },
                'tags': [],
                'version': [
                    {
                        'identifier': '2',
                        'size': 4001,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion264charsversion264charsversion264charsversion264ch',
                            'provider': 's3compat'
                        }
                    },
                    {
                        'identifier': '1',
                        'size': 4000,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion164charsversion164charsversion164charsversion164ch',
                            'provider': 's3compat'
                        }
                    }
                ],
                'size': 4001,
                'location': {
                    'object': '64charsversion264charsversion264charsversion264charsversion264ch',
                    'provider': 's3compat'
                },
                'timestamp': {},
                'checkout_id': None
            },
            {
                'id': 5000,
                'path': '/24chars24chars24chars24c',
                'materialized_path': '/folder_path/file_name.ext',
                'name': 'file_name.ext',
                'provider': 'osfstorage',
                'project': {
                    'id': 'prjid',
                    'name': 'PRJ 20231005 001'
                },
                'tags': [],
                'version': [
                    {
                        'identifier': '2',
                        'size': 5001,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion264charsversion264charsversion264charsversion264ch',
                            'provider': 's3compat'
                        }
                    },
                    {
                        'identifier': '1',
                        'size': 5000,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion164charsversion164charsversion164charsversion164ch',
                            'provider': 's3compat'
                        }
                    }
                ],
                'size': 5001,
                'location': {
                    'object': '64charsversion264charsversion264charsversion264charsversion264ch',
                    'provider': 's3compat'
                },
                'timestamp': {},
                'checkout_id': None
            },
            {
                'id': 6000,
                'path': '/24chars24chars24chars24c',
                'materialized_path': '/folder_path/file_name.ext',
                'name': 'file_name.ext',
                'provider': 'osfstorage',
                'project': {
                    'id': 'prjid',
                    'name': 'PRJ 20231005 001'
                },
                'tags': [],
                'version': [
                    {
                        'identifier': '6',
                        'size': 6005,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion664charsversion664charsversion664charsversion664ch',
                            'provider': 's3compat'
                        }
                    },
                    {
                        'identifier': '5',
                        'size': 6004,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion564charsversion564charsversion564charsversion564ch',
                            'provider': 's3compat'
                        }
                    },
                    {
                        'identifier': '4',
                        'size': 6003,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion464charsversion464charsversion464charsversion464ch',
                            'provider': 's3compat'
                        }
                    },
                    {
                        'identifier': '3',
                        'size': 6002,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion364charsversion364charsversion364charsversion364ch',
                            'provider': 's3compat'
                        }
                    },
                    {
                        'identifier': '2',
                        'size': 6001,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion264charsversion264charsversion264charsversion264ch',
                            'provider': 's3compat'
                        }
                    },
                    {
                        'identifier': '1',
                        'size': 6000,
                        'version_name': 'file_name.ext',
                        'metadata': {
                            'kind': 'file',
                        },
                        'location': {
                            'object': '64charsversion164charsversion164charsversion164charsversion164ch',
                            'provider': 's3compat'
                        }
                    }
                ],
                'size': 6005,
                'location': {
                    'object': '64charsversion664charsversion664charsversion664charsversion664ch',
                    'provider': 's3compat'
                },
                'timestamp': {},
                'checkout_id': None
            },
        ]

    def test_separate_failed_files__c1_empty_version_ids(self):
        files_versions_not_found = {
            1000: [],
        }
        expected_sub_size = 0
        expected_sub_files_numb = 0

        _files_not_found, _sub_size, _sub_files_numb = export.separate_failed_files(
            self.files,
            files_versions_not_found
        )

        self.assertEqual(_files_not_found, [])
        self.assertEqual(_sub_size, expected_sub_size)
        self.assertEqual(_sub_files_numb, expected_sub_files_numb)

    def test_separate_failed_files__c2_not_found_in_files(self):
        files_versions_not_found = {
            2000: ['1'],
        }
        expected_sub_size = 0
        expected_sub_files_numb = 0

        _files_not_found, _sub_size, _sub_files_numb = export.separate_failed_files(
            self.files,
            files_versions_not_found
        )

        self.assertEqual(_files_not_found, [])
        self.assertEqual(_sub_size, expected_sub_size)
        self.assertEqual(_sub_files_numb, expected_sub_files_numb)

    def test_separate_failed_files__c3_file_no_versions(self):
        files_versions_not_found = {
            3000: ['1'],
        }
        file_id = 3000
        expected_sub_size = 0
        expected_sub_files_numb = 0

        _files_not_found, _sub_size, _sub_files_numb = export.separate_failed_files(
            self.files,
            files_versions_not_found
        )

        file = next(
            (_file for idx, _file in enumerate(self.files) if file_id == _file['id']),
            None  # default
        )
        self.assertEqual(file, None)
        self.assertEqual(len(_files_not_found), 1)
        file = _files_not_found[0]
        versions = file.get('version', [])
        self.assertEqual(file['id'], file_id)
        self.assertEqual(versions, [])
        self.assertEqual(_sub_size, expected_sub_size)
        self.assertEqual(_sub_files_numb, expected_sub_files_numb)

    def test_separate_failed_files__c4_match_all_versions(self):
        files_versions_not_found = {
            4000: ['1', '2'],
        }
        file_id = 4000

        _files_not_found, _sub_size, _sub_files_numb = export.separate_failed_files(
            self.files,
            files_versions_not_found
        )

        file = next(
            (_file for idx, _file in enumerate(self.files) if file_id == _file['id']),
            None  # default
        )
        self.assertEqual(file, None)
        self.assertEqual(len(_files_not_found), 1)
        file = _files_not_found[0]
        self.assertEqual(file['id'], file_id)
        versions = file.get('version', [])
        not_found_ver_ids_set = set(files_versions_not_found[file_id])
        found_ver_ids_set = set([_ver['identifier'] for _ver in versions])
        self.assertEqual(found_ver_ids_set, not_found_ver_ids_set)
        self.assertEqual(_sub_size, sum([ver.get('size') for ver in versions]))
        self.assertEqual(_sub_files_numb, len(versions))

    def test_separate_failed_files__c5_match_no_versions(self):
        files_versions_not_found = {
            5000: ['10'],
        }
        file_id = 5000
        expected_sub_size = 0
        expected_sub_files_numb = 0

        _files_not_found, _sub_size, _sub_files_numb = export.separate_failed_files(
            self.files,
            files_versions_not_found
        )

        file = next(
            (_file for idx, _file in enumerate(self.files) if file_id == _file['id']),
            None  # default
        )
        self.assertEqual(file['id'], file_id)
        self.assertEqual(len(_files_not_found), 0)
        self.assertEqual(_sub_size, expected_sub_size)
        self.assertEqual(_sub_files_numb, expected_sub_files_numb)

    def test_separate_failed_files__c6_match_some_versions(self):
        files_versions_not_found = {
            6000: ['3', '5'],
        }
        file_id = 6000

        _files_not_found, _sub_size, _sub_files_numb = export.separate_failed_files(
            self.files,
            files_versions_not_found
        )

        file = next(
            (_file for idx, _file in enumerate(self.files) if file_id == _file['id']),
            None  # default
        )
        self.assertEqual(file['id'], file_id)
        versions = file.get('version', [])
        found_ver_ids_set = set([_ver['identifier'] for _ver in versions])
        self.assertEqual(len(_files_not_found), 1)
        file = _files_not_found[0]
        self.assertEqual(file['id'], file_id)
        versions = file.get('version', [])
        _not_found_ver_ids_set = set(files_versions_not_found[file_id])
        not_found_ver_ids_set = set([_ver['identifier'] for _ver in versions])
        self.assertEqual(not_found_ver_ids_set, _not_found_ver_ids_set)
        self.assertEqual(not_found_ver_ids_set - found_ver_ids_set, _not_found_ver_ids_set)
        self.assertEqual(_sub_size, sum([ver.get('size') for ver in versions]))
        self.assertEqual(_sub_files_numb, len(versions))


class TestExportDataProcess(unittest.TestCase):
    def setUp(self):
        super(TestExportDataProcess, self).setUp()
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID
        self.other_task = AbortableTask()
        self.other_task.request_stack = LocalStack()
        self.other_task.request.id = FAKE_TASK_ID[:-1] + '1'

        self.request = RequestFactory().post('export_data', {})
        self.request.user = self.user

        self.cookies = 'abcd'

        self.export_data = ExportDataFactory(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id,
            status=ExportData.STATUS_RUNNING
        )

    def update_fake(self, *args, **kwargs):
        if kwargs.get('status') == ExportData.STATUS_STOPPING:
            self.export_data.status = ExportData.STATUS_STOPPING
            self.export_data.save()
        elif kwargs.get('status') == ExportData.STATUS_STOPPED:
            self.export_data.status = ExportData.STATUS_STOPPED
            self.export_data.save()
        elif kwargs.get('status') == ExportData.STATUS_RUNNING:
            self.export_data.status = ExportData.STATUS_RUNNING
            self.export_data.save()
        elif kwargs.get('status') == ExportData.STATUS_COMPLETED:
            self.export_data.status = ExportData.STATUS_COMPLETED
            self.export_data.save()

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_process__raise_export_data_removed(
            self, mock_export_data):
        mock_export_data.filter.return_value.first.return_value = None
        mock_export_data.filter.return_value.exists.return_value = False

        with self.assertRaises(Ignore):
            export.export_data_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_REMOVED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.delete_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_process__raise_exception(
            self, mock_export_data,
            mock_extract_json,
            mock_delete_export_data_folder,
    ):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        mock_extract_json.side_effect = Exception('some error')
        mock_delete_export_data_folder.side_effect = Exception('some os error')

        with self.assertRaises(Ignore):
            export.export_data_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_ERROR)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_not_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_not_equal(_task_result.get('exc_message'), export.MSG_EXPORT_COMPLETED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)
            nt.assert_not_equal(_task_result.get('traceback'), None)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_process__raise_task_aborted(
            self, mock_export_data, mock_extract_json):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        export_data_json = file_info_json = {}

        def do_something():
            _task = AbortableAsyncResult(self.task.request.id)
            _task.abort()
            return export_data_json, file_info_json

        mock_extract_json.side_effect = do_something

        with self.assertRaises(Ignore):
            export.export_data_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_ERROR)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_ABORTED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.delete_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_process__rollback_raise(
            self, mock_export_data,
            mock_extract_json,
            mock_create_export_data_folder,
            mock_create_export_data_files_folder,
            mock_delete_export_data_folder
    ):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        export_data_json = file_info_json = {}
        mock_extract_json.return_value = export_data_json, file_info_json
        mock_create_export_data_folder.return_value.status_code = status.HTTP_201_CREATED
        mock_create_export_data_files_folder.return_value.status_code = status.HTTP_400_BAD_REQUEST
        mock_delete_export_data_folder.return_value.status_code = status.HTTP_204_NO_CONTENT

        with self.assertRaises(Ignore):
            export.export_data_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_ERROR)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_STOPPED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_full_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.write_json_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_export_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.copy_export_data_file_to_location')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_process__return_completed(
            self, mock_export_data,
            mock_extract_json,
            mock_create_export_data_folder,
            mock_create_export_data_files_folder,
            mock_get_source_file_versions_min,
            mock_copy_export_data_file_to_location,
            mock_upload_file_info_file,
            mock_upload_export_data_file,
            mock_write_json_file,
            mock_upload_file_info_full_data_file
    ):
        mock_write_json_file.return_value = None
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        export_data_json = {
            'institution': {
                'id': self.institution.id,
                'guid': self.institution.guid,
                'name': self.institution.name,
            },
            'process_start': '%Y-%m-%d %H:%M:%S',
            'process_end': None,
            'storage': {
                'name': self.source.name,
                'type': self.source.provider_full_name,
            },
            'projects_numb': 1,
            'files_numb': 0,
            'size': 0,
            'file_path': self.export_data.get_file_info_file_path(),
        }
        file_info_json = {}
        mock_extract_json.return_value = export_data_json, file_info_json
        mock_create_export_data_folder.return_value.status_code = status.HTTP_201_CREATED
        mock_create_export_data_files_folder.return_value.status_code = status.HTTP_201_CREATED
        file_versions = []
        mock_get_source_file_versions_min.return_value = file_versions
        mock_copy_export_data_file_to_location.return_value.status_code = status.HTTP_201_CREATED
        mock_upload_file_info_file.return_value.status_code = status.HTTP_201_CREATED
        mock_upload_export_data_file.return_value.status_code = status.HTTP_201_CREATED
        mock_upload_file_info_full_data_file.return_value.status_code = status.HTTP_201_CREATED

        _task_result = export.export_data_process(
            self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
        )
        self.task.update_state(state=states.SUCCESS, meta=_task_result)

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_true(task_result.state in states.READY_STATES)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_COMPLETED)
        nt.assert_equal(_task_result.get('message'), export.MSG_EXPORT_COMPLETED)
        nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
        nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)
        nt.assert_equal(_task_result.get('list_file_info_export_not_found'), [])
        nt.assert_equal(_task_result.get('file_name_export_fail'), 'failed_files_export_{}_{}.csv'.format(
            export_data_json.get('institution').get('guid'),
            self.export_data.process_start_timestamp
        ))

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.write_json_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_export_data_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.upload_file_info_file')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.copy_export_data_file_to_location')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.get_source_file_versions_min')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_files_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.create_export_data_folder')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.extract_file_information_json_from_source_storage')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_process__connection_timeout(
            self, mock_export_data,
            mock_extract_json,
            mock_create_export_data_folder,
            mock_create_export_data_files_folder,
            mock_get_source_file_versions_min,
            mock_copy_export_data_file_to_location,
            mock_upload_file_info_file,
            mock_upload_export_data_file,
            mock_write_json_file,
    ):
        mock_write_json_file.return_value = None
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        export_data_json = {
            'institution': {
                'id': self.institution.id,
                'guid': self.institution.guid,
                'name': self.institution.name,
            },
            'process_start': '%Y-%m-%d %H:%M:%S',
            'process_end': None,
            'storage': {
                'name': self.source.name,
                'type': self.source.provider_full_name,
            },
            'projects_numb': 1,
            'files_numb': 0,
            'size': 0,
            'file_path': self.export_data.get_file_info_file_path(),
        }
        file_info_json = {}
        mock_extract_json.return_value = export_data_json, file_info_json
        mock_create_export_data_folder.return_value.status_code = status.HTTP_201_CREATED
        mock_create_export_data_files_folder.return_value.status_code = status.HTTP_201_CREATED
        file_versions = []
        mock_get_source_file_versions_min.return_value = file_versions
        mock_copy_export_data_file_to_location.side_effect = Exception('ConnectionError')
        mock_upload_file_info_file.return_value.status_code = status.HTTP_201_CREATED
        mock_upload_export_data_file.return_value.status_code = status.HTTP_201_CREATED

        _task_result = export.export_data_process(
            self.task, self.cookies, self.export_data.id, self.location.id, self.source.id
        )
        self.task.update_state(state=states.SUCCESS, meta=_task_result)

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_true(task_result.state in states.READY_STATES)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_COMPLETED)
        nt.assert_equal(_task_result.get('message'), export.MSG_EXPORT_COMPLETED)
        nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
        nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)
        nt.assert_equal(_task_result.get('list_file_info_export_not_found'), [])
        nt.assert_equal(_task_result.get('file_name_export_fail'), 'failed_files_export_{}_{}.csv'.format(
            export_data_json.get('institution').get('guid'),
            self.export_data.process_start_timestamp
        ))


class TestExportDataRollbackProcess(unittest.TestCase):
    def setUp(self):
        super(TestExportDataRollbackProcess, self).setUp()
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID
        self.other_task = AbortableTask()
        self.other_task.request_stack = LocalStack()
        self.other_task.request.id = FAKE_TASK_ID[:-1] + '1'

        self.request = RequestFactory().post('export_data', {})
        self.request.user = self.user

        self.cookies = 'abcd'

        self.export_data = ExportDataFactory(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id,
            status=ExportData.STATUS_RUNNING
        )

    def update_fake(self, *args, **kwargs):
        if kwargs.get('status') == ExportData.STATUS_STOPPING:
            self.export_data.status = ExportData.STATUS_STOPPING
            self.export_data.save()
        elif kwargs.get('status') == ExportData.STATUS_STOPPED:
            self.export_data.status = ExportData.STATUS_STOPPED
            self.export_data.save()
        elif kwargs.get('status') == ExportData.STATUS_RUNNING:
            self.export_data.status = ExportData.STATUS_RUNNING
            self.export_data.save()
        elif kwargs.get('status') == ExportData.STATUS_COMPLETED:
            self.export_data.status = ExportData.STATUS_COMPLETED
            self.export_data.save()

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__raise_export_data_removed(
            self, mock_export_data):
        mock_export_data.filter.return_value.first.return_value = None
        mock_export_data.filter.return_value.exists.return_value = False

        with self.assertRaises(Ignore):
            export.export_data_rollback_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
                export_data_task=self.other_task.request.id,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_REMOVED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_task_id'), self.other_task.request.id)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__raise_cannot_stop_stopping_process(
            self, mock_export_data):
        # for export_data.status not in [STATUS_PENDING, STATUS_RUNNING, ExportData.STATUS_STOPPED]
        self.export_data.status = ExportData.STATUS_STOPPING
        self.export_data.save()
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True

        with self.assertRaises(Ignore):
            export.export_data_rollback_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
                export_data_task=self.other_task.request.id,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_ERROR)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_UNSTOPPABLE)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_task_id'), self.other_task.request.id)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__raise_cannot_stop_stopped_process(
            self, mock_export_data):
        self.export_data.status = ExportData.STATUS_STOPPED
        self.export_data.save()
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True

        with self.assertRaises(Ignore):
            export.export_data_rollback_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
                export_data_task=self.other_task.request.id,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_STOPPED)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_UNSTOPPABLE)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_task_id'), self.other_task.request.id)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__rollback_raise_exception(
            self, mock_export_data):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data

        with self.assertRaises(Ignore):
            export.export_data_rollback_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
                is_rollback=True,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_ERROR)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_not_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_not_equal(_task_result.get('exc_message'), export.MSG_EXPORT_STOPPED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_task_id'), None)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)
            nt.assert_not_equal(_task_result.get('traceback'), None)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__rollback_stopped_process(
            self, mock_export_data):
        self.export_data.status = ExportData.STATUS_STOPPED
        self.export_data.save()
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data

        with self.assertRaises(Ignore):
            export.export_data_rollback_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
                is_rollback=True,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_STOPPED)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_STOPPED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_task_id'), None)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)
            nt.assert_equal(_task_result.get('traceback'), None)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__rollback_raise_stopped(
            self, mock_export_data):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        self.export_data.delete_export_data_folder = mock_method = mock.Mock()
        mock_method.return_value.status_code = status.HTTP_204_NO_CONTENT

        with self.assertRaises(Ignore):
            export.export_data_rollback_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
                is_rollback=True,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_ERROR)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_STOPPED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_task_id'), None)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__rollback_raise_stopped_with_warning(
            self, mock_export_data):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        self.export_data.delete_export_data_folder = mock_method = mock.Mock()
        mock_method.return_value.status_code = status.HTTP_400_BAD_REQUEST

        with self.assertRaises(Ignore):
            export.export_data_rollback_process(
                self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
                is_rollback=True,
            )

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(task_result.state, states.FAILURE)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_ERROR)
        task_record_set = TaskResult.objects.filter(task_id=self.task.request.id)
        if task_record_set:
            task_record = task_record_set.first()
            _task_result = json.loads(task_record.result)
            nt.assert_equal(_task_result.get('exc_type'), 'ExportDataTaskException')
            nt.assert_equal(_task_result.get('exc_message'), export.MSG_EXPORT_FORCE_STOPPED)
            nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
            nt.assert_equal(_task_result.get('export_data_task_id'), None)
            nt.assert_equal(_task_result.get('export_data_status'), self.export_data.status)

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__return_stopped(
            self, mock_export_data):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        self.export_data.delete_export_data_folder = mock_method = mock.Mock()
        mock_method.return_value.status_code = status.HTTP_204_NO_CONTENT

        _task_result = export.export_data_rollback_process(
            self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
            export_data_task=self.other_task.request.id,
        )
        self.task.update_state(state=states.SUCCESS, meta=_task_result)

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_STOPPED)
        nt.assert_true(task_result.state in states.READY_STATES)
        nt.assert_equal(_task_result.get('message'), export.MSG_EXPORT_STOPPED)
        nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
        nt.assert_equal(_task_result.get('export_data_task_id'), self.other_task.request.id)
        nt.assert_equal(_task_result.get('export_data_status'), ExportData.STATUS_STOPPED)
        other_task_result = AbortableAsyncResult(self.other_task.request.id)
        nt.assert_equal(_task_result.get('export_data_task_result'), export.get_task_result(other_task_result.result))

    @pytest.mark.django_db
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_export_data_rollback_process__return_stopped_with_warning(
            self, mock_export_data):
        mock_export_data.filter.return_value.first.return_value = self.export_data
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.get.return_value = self.export_data
        self.export_data.delete_export_data_folder = mock_method = mock.Mock()
        mock_method.return_value.status_code = status.HTTP_400_BAD_REQUEST

        _task_result = export.export_data_rollback_process(
            self.task, self.cookies, self.export_data.id, self.location.id, self.source.id,
            export_data_task=self.other_task.request.id,
        )
        self.task.update_state(state=states.SUCCESS, meta=_task_result)

        task_result = AbortableAsyncResult(self.task.request.id)
        nt.assert_true(task_result.state in states.READY_STATES)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_STOPPED)
        nt.assert_equal(_task_result.get('message'), export.MSG_EXPORT_FORCE_STOPPED)
        nt.assert_equal(_task_result.get('export_data_id'), self.export_data.id)
        nt.assert_equal(_task_result.get('export_data_task_id'), self.other_task.request.id)
        nt.assert_equal(_task_result.get('export_data_status'), ExportData.STATUS_STOPPED)
        other_task_result = AbortableAsyncResult(self.other_task.request.id)
        nt.assert_equal(_task_result.get('export_data_task_result'), export.get_task_result(other_task_result.result))


class TestExportDataBaseActionView(AdminTestCase):
    def setUp(self):
        super(TestExportDataBaseActionView, self).setUp()

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.view = export.ExportDataBaseActionView()
        self.view.request = self.request

    def test_extract_input__no_institution_id(self):
        self.request.data = {
            'institution_id': None,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.status_code, status.HTTP_400_BAD_REQUEST)
        nt.assert_equal(res.data['message'], export.MSG_EXPORT_MISSING_REQUIRED_INPUT)

    def test_extract_input__not_exists_institution_id(self):
        self.request.data = {
            'institution_id': -1,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.status_code, status.HTTP_404_NOT_FOUND)
        nt.assert_equal(res.data['message'], export.MSG_EXPORT_NOT_EXIST_INPUT)

    def test_extract_input__not_admin_not_superuser(self):
        self.user.is_staff = False
        self.user.save()

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.status_code, status.HTTP_403_FORBIDDEN)
        nt.assert_equal(res.data['message'], export.MSG_EXPORT_DENY_PERM_INST)

    def test_extract_input__admin_not_affiliated_institution_id(self):
        self.request.data = {
            'institution_id': self.other_institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.status_code, status.HTTP_403_FORBIDDEN)
        nt.assert_equal(res.data['message'], export.MSG_EXPORT_DENY_PERM_INST)

    def test_extract_input__no_source_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': None,
            'location_id': self.location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.data['message'], export.MSG_EXPORT_MISSING_REQUIRED_INPUT)
        nt.assert_equal(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extract_input__not_exists_source_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': -1,
            'location_id': self.location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.data['message'], export.MSG_EXPORT_NOT_EXIST_INPUT)
        nt.assert_equal(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_extract_input__not_allowed_source_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.other_source.id,
            'location_id': self.location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.data['message'], export.MSG_EXPORT_DENY_PERM_STORAGE)
        nt.assert_equal(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_extract_input__no_location_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': None,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.data['message'], export.MSG_EXPORT_MISSING_REQUIRED_INPUT)
        nt.assert_equal(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_extract_input__no_exists_location_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': -1,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.data['message'], export.MSG_EXPORT_NOT_EXIST_INPUT)
        nt.assert_equal(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_extract_input__no_allowed_location_id(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.other_location.id,
        }

        res = self.view.extract_input(self.request)

        nt.assert_equal(res.data['message'], export.MSG_EXPORT_DENY_PERM_LOCATION)
        nt.assert_equal(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_extract_input__success_as_admin_affiliated_institution(self):
        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        institution, source_storage, location = self.view.extract_input(self.request)

        nt.assert_equal(institution.id, self.institution.id)
        nt.assert_equal(source_storage.id, self.source.id)
        nt.assert_equal(location.id, self.location.id)

    def test_extract_input__success_as_superuser(self):
        self.user.is_superuser = True
        self.user.save()

        self.request.data = {
            'institution_id': self.other_institution.id,
            'source_id': self.other_source.id,
            'location_id': self.other_location.id,
        }

        institution, source_storage, location = self.view.extract_input(self.request)

        nt.assert_equal(institution.id, self.other_institution.id)
        nt.assert_equal(source_storage.id, self.other_source.id)
        nt.assert_equal(location.id, self.other_location.id)


class TestExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestExportDataActionView, self).setUp()
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID
        self.other_task = AbortableTask()
        self.other_task.request_stack = LocalStack()
        self.other_task.request.id = FAKE_TASK_ID[:-1] + '1'

        self.request = RequestFactory().post('export_data', {})
        self.request.user = self.user

        self.view = export.ExportDataActionView()
        self.view.request = self.request

    def test_post__403_not_admin(self):
        self.user.is_staff = False
        self.user.save()

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.extract_input(self.request)

        nt.assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        nt.assert_equal(response.data['message'], export.MSG_EXPORT_DENY_PERM_INST)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__400_integrity_error(self, mock_export_data):
        mock_export_data.filter.return_value.exists.return_value = False

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        with mock.patch('osf.models.ExportData.objects.create', side_effect=IntegrityError('mocked error')):
            response = self.view.post(self.request)
            nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)
            nt.assert_equal(response.data.get('message'), export.MSG_EXPORT_DUP_IN_SECOND)

    @mock.patch(f'{EXPORT_DATA_TASK_PATH}.run_export_data_process.delay')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult._get_task_meta')
    def test_post__200_success(self, mock_async_result, mock_export_data, mock_task):
        mock_task.return_value = AbortableAsyncResult(self.task.request.id)
        mock_async_result.return_value = {
            'status': states.PENDING,
            'result': {}
        }
        export_data = ExportDataFactory(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id,
            status=ExportData.STATUS_PENDING
        )
        mock_export_data.create.return_value = export_data
        mock_export_data.filter.return_value.first.return_value = export_data

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_200_OK)
        nt.assert_equal(response.data.get('task_id'), self.task.request.id)
        nt.assert_equal(response.data.get('task_state'), states.PENDING)
        nt.assert_equal(response.data.get('result'), {})
        nt.assert_equal(response.data.get('status'), export_data.status)


class TestStopExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestStopExportDataActionView, self).setUp()
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID
        self.other_task = AbortableTask()
        self.other_task.request_stack = LocalStack()
        self.other_task.request.id = FAKE_TASK_ID[:-1] + '1'

        self.request = RequestFactory().post('export_data', {})
        self.request.user = self.user

        self.view = export.StopExportDataActionView()
        self.view.request = self.request

    def test_post__403_not_admin(self):
        self.user.is_staff = False
        self.user.save()

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.extract_input(self.request)

        nt.assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        nt.assert_equal(response.data['message'], export.MSG_EXPORT_DENY_PERM_INST)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__400_no_task_id(self, mock_export_data):
        mock_export_data.filter.return_value.exists.return_value = True

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': None,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)
        nt.assert_equal(response.data.get('message'), export.MSG_EXPORT_NOT_EXIST_INPUT)
        nt.assert_equal(response.data.get('task_id'), None)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__400_no_export_data(self, mock_export_data):
        mock_export_data.filter.return_value.exists.return_value = False

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)
        nt.assert_equal(response.data.get('message'), export.MSG_EXPORT_NOT_EXIST_INPUT)
        nt.assert_equal(response.data.get('task_id'), self.task.request.id)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult._get_task_meta')
    def test_post__400_task_finished(self, mock_async_result, mock_export_data):
        mock_async_result.return_value = {
            'status': states.SUCCESS,
            'result': {}
        }
        export_data = ExportData(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id
        )
        mock_export_data.filter.return_value.first.return_value = export_data

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)
        nt.assert_equal(response.data.get('message'), export.MSG_EXPORT_UNSTOPPABLE)
        nt.assert_equal(response.data.get('task_id'), self.task.request.id)
        nt.assert_equal(response.data.get('task_state'), states.SUCCESS)
        nt.assert_equal(response.data.get('status'), export_data.status)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult._get_task_meta')
    def test_post__400_fail_abort(self, mock_async_result, mock_export_data):
        mock_async_result.return_value = {
            'status': states.STARTED,
            'result': {}
        }
        export_data = ExportData(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id,
            status=ExportData.STATUS_RUNNING
        )
        mock_export_data.filter.return_value.first.return_value = export_data

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_400_BAD_REQUEST)
        nt.assert_equal(response.data.get('message'), export.MSG_EXPORT_UNABORTABLE)
        nt.assert_equal(response.data.get('task_id'), self.task.request.id)
        nt.assert_equal(response.data.get('task_state'), states.STARTED)
        nt.assert_equal(response.data.get('status'), export_data.status)

    @mock.patch(f'{EXPORT_DATA_TASK_PATH}.run_export_data_rollback_process.delay')
    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult._get_task_meta')
    def test_post__200_success_abort(self, mock_async_result, mock_export_data, mock_task):
        mock_task.return_value = AbortableAsyncResult(self.other_task.request.id)
        mock_async_result.return_value = {
            'status': ABORTED,
            'result': {}
        }
        export_data = ExportData(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id,
            status=ExportData.STATUS_RUNNING
        )
        mock_export_data.filter.return_value.exists.return_value = True
        mock_export_data.filter.return_value.first.return_value = export_data
        mock_export_data.get.return_value = export_data

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_200_OK)
        nt.assert_equal(response.data.get('task_id'), self.other_task.request.id)
        nt.assert_equal(response.data.get('task_state'), ABORTED)
        nt.assert_equal(response.data.get('result'), {})
        nt.assert_equal(response.data.get('status'), export_data.status)


class TestCheckStateExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestCheckStateExportDataActionView, self).setUp()

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.view = export.CheckStateExportDataActionView()
        self.view.request = self.request

    def test_post__403_not_admin(self):
        self.user.is_staff = False
        self.user.save()

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.extract_input(self.request)

        nt.assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        nt.assert_equal(response.data['message'], export.MSG_EXPORT_DENY_PERM_INST)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__400_no_task_id(self, mock_export_data):
        mock_export_data.filter.return_value.exists.return_value = True

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': None,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)
        nt.assert_equal(response.data.get('message'), export.MSG_EXPORT_NOT_EXIST_INPUT)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__400_no_export_data(self, mock_export_data):
        mock_export_data.filter.return_value.exists.return_value = False

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_404_NOT_FOUND)
        nt.assert_equal(response.data.get('message'), export.MSG_EXPORT_NOT_EXIST_INPUT)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    @mock.patch('celery.contrib.abortable.AbortableAsyncResult._get_task_meta')
    def test_post__200(self, mock_async_result, mock_export_data):
        mock_async_result.return_value = {
            'status': states.STARTED,
            'result': {}
        }
        export_data = ExportData(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id
        )
        mock_export_data.filter.return_value.first.return_value = export_data

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
            'task_id': self.task.request.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_200_OK)
        nt.assert_equal(response.data.get('task_id'), self.task.request.id)
        nt.assert_equal(response.data.get('task_state'), states.STARTED)
        nt.assert_equal(response.data.get('result'), {})
        nt.assert_equal(response.data.get('status'), export_data.status)


class TestCheckDataExportDataActionView(AdminTestCase):
    def setUp(self):
        super(TestCheckDataExportDataActionView, self).setUp()

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.view = export.CheckDataExportDataActionView()
        self.view.request = self.request

    def test_post__403_not_admin(self):
        self.user.is_staff = False
        self.user.save()

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        response = self.view.extract_input(self.request)

        nt.assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        nt.assert_equal(response.data['message'], export.MSG_EXPORT_DENY_PERM_INST)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__200_has_data(self, mock_export_data):
        mock_export_data.filter.return_value.exists.return_value = True

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_200_OK)
        nt.assert_equal(response.data['has_data'], True)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__200_not_has_data(self, mock_export_data):
        mock_export_data.filter.return_value.exists.return_value = False

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_200_OK)
        nt.assert_equal(response.data['has_data'], False)


class TestCheckRunningExportActionView(AdminTestCase):
    def setUp(self):
        super(TestCheckRunningExportActionView, self).setUp()

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()
        self.other_source = RegionFactory()
        self.other_source._id = self.other_institution._id
        self.other_source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()
        self.other_location = ExportDataLocationFactory()
        self.other_location.institution_guid = self.other_institution._id
        self.other_location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user

        self.view = export.CheckRunningExportActionView()
        self.view.request = self.request

    def test_post__403_not_admin(self):
        self.user.is_staff = False
        self.user.save()

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        response = self.view.extract_input(self.request)

        nt.assert_equal(response.status_code, status.HTTP_403_FORBIDDEN)
        nt.assert_equal(response.data['message'], export.MSG_EXPORT_DENY_PERM_INST)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__200_has_task(self, mock_export_data):
        export_data = ExportData(
            creator=self.user,
            source=self.source,
            location=self.location,
            status=ExportData.STATUS_RUNNING,
            task_id=self.task.request.id
        )
        mock_export_data.filter.return_value = [export_data]

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_200_OK)
        nt.assert_equal(response.data.get('task_id'), export_data.task_id)

    @mock.patch(f'{EXPORT_DATA_PATH}.ExportData.objects')
    def test_post__200_no_task(self, mock_export_data):
        mock_export_data.filter.return_value = []

        self.request.data = {
            'institution_id': self.institution.id,
            'source_id': self.source.id,
            'location_id': self.location.id,
        }

        response = self.view.post(self.request)

        nt.assert_equal(response.status_code, status.HTTP_200_OK)
        nt.assert_equal(response.data.get('task_id'), None)


class TestCheckExportDataProcessStatus(AdminTestCase):
    def setUp(self):
        super(TestCheckExportDataProcessStatus, self).setUp()
        celery_app.conf.update({
            'task_always_eager': False,
            'task_eager_propagates': False,
        })

        self.institution = InstitutionFactory()
        self.other_institution = InstitutionFactory()

        self.source = RegionFactory()
        self.source._id = self.institution._id
        self.source.save()

        self.location = ExportDataLocationFactory()
        self.location.institution_guid = self.institution._id
        self.location.save()

        self.user = AuthUserFactory()
        self.user.is_active = True
        self.user.is_registered = True
        self.user.is_staff = True
        self.user.is_superuser = False
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        self.task = AbortableTask()
        self.task.request_stack = LocalStack()
        self.task.request.id = FAKE_TASK_ID
        self.other_task = AbortableTask()
        self.other_task.request_stack = LocalStack()
        self.other_task.request.id = FAKE_TASK_ID[:-1] + '1'

        self.export_data = ExportDataFactory(
            creator=self.user,
            source=self.source,
            location=self.location,
            task_id=self.task.request.id,
            status=ExportData.STATUS_RUNNING
        )

    def test_check_export_data_process_status__c1_not_pass_interval(self):
        _start_time = time.time()
        _prev_time = export.check_export_data_process_status(_start_time, self.task.request.id)
        self.assertEqual(_prev_time, _start_time)

    def test_check_export_data_process_status__c2_is_forced(self):
        _start_time = time.time()
        self.task.update_state(state=states.STARTED, meta={})
        _prev_time = export.check_export_data_process_status(
            _start_time, self.task.request.id,
            is_force=True
        )
        self.assertNotEqual(_prev_time, _start_time)

        self.task.update_state(state=states.STARTED, meta={})
        _prev_time = export.check_export_data_process_status(
            _start_time, self.task.request.id,
            location_id=self.location.id,
            source_id=self.source.id,
            export_data_id=self.export_data.id,
            is_force=True
        )
        self.assertNotEqual(_prev_time, _start_time)

    def test_check_export_data_process_status__c3_task_is_aborted(self):
        _start_time = time.time()
        self.task.update_state(state=ABORTED, meta={})
        with self.assertRaises(export.ExportDataTaskException):
            export.check_export_data_process_status(
                _start_time, self.task.request.id, is_force=True
            )

    def test_check_export_data_process_status__c4_location_not_exist(self):
        _start_time = time.time()
        location_id = self.location.id
        self.location.delete()
        with self.assertRaises(export.ExportDataTaskException):
            export.check_export_data_process_status(
                _start_time, self.task.request.id,
                location_id=location_id,
                is_force=True
            )

    def test_check_export_data_process_status__c5_source__not_exist(self):
        _start_time = time.time()
        source_id = self.source.id
        self.source.delete()
        with self.assertRaises(export.ExportDataTaskException):
            export.check_export_data_process_status(
                _start_time, self.task.request.id,
                location_id=self.location.id,
                source_id=source_id,
                is_force=True
            )

    def test_check_export_data_process_status__c6_export_data__not_exist(self):
        _start_time = time.time()
        export_data_id = self.export_data.id
        self.export_data.delete()
        with self.assertRaises(export.ExportDataTaskException):
            export.check_export_data_process_status(
                _start_time, self.task.request.id,
                location_id=self.location.id,
                source_id=self.source.id,
                export_data_id=export_data_id,
                is_force=True
            )
