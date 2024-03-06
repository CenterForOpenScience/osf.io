import copy
from datetime import datetime

import mock
import pytest
from addons.osfstorage.tests.factories import FileVersionFactory
from django.http import JsonResponse
from django.test import TestCase
from nose import tools as nt

from addons.osfstorage.models import Region
from addons.osfstorage.settings import DEFAULT_REGION_ID
from osf.models import AbstractNode, ExportData
from osf.models.export_data import DateTruncMixin
from osf_tests.factories import (
    TagFactory,
    RegionFactory,
    ProjectFactory,
    AuthUserFactory,
    ExportDataFactory,
    InstitutionFactory,
    OsfStorageFileFactory,
    ExportDataRestoreFactory,
    BaseFileVersionsThroughFactory,
    RdmFileTimestamptokenVerifyResultFactory,
)
from admin_tests.rdm_custom_storage_location.export_data.test_utils import FAKE_DATA


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestExportData(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.default_region = default_region = Region.objects.get(_id=DEFAULT_REGION_ID)
        cls.inst_region = inst_region = RegionFactory(
            name=default_region.name,
            waterbutler_credentials=default_region.waterbutler_credentials,
            waterbutler_settings=default_region.waterbutler_settings
        )
        cls.institution = InstitutionFactory.create(_id=inst_region.guid)
        cls.export_data = ExportDataFactory(source=inst_region)
        project = ProjectFactory()
        target = AbstractNode(id=project.id)
        cls.institution.nodes.set([project])
        cls.file1 = file1 = OsfStorageFileFactory.create(
            name='file1.txt',
            created=datetime.now(),
            target_object_id=project.id,
            target=target
        )
        file_version = FileVersionFactory(region=inst_region, size=3,)
        file_versions_through = BaseFileVersionsThroughFactory.create(
            version_name=file1.name,
            basefilenode=file1,
            fileversion=file_version
        )
        file_versions = [file_version]
        total_size = sum([f.size for f in file_versions])
        files_numb = len(file_versions)

        cls.institution_json = {
            'id': cls.institution.id,
            'guid': cls.institution.guid,
            'name': cls.institution.name
        }
        cls.export_data_json = {
            'institution': cls.institution_json,
            'process_start': cls.export_data.process_start.strftime('%Y-%m-%d %H:%M:%S'),
            'process_end': cls.export_data.process_end.strftime(
                '%Y-%m-%d %H:%M:%S') if cls.export_data.process_end else None,
            'storage': {
                'name': cls.export_data.source.name,
                'type': cls.export_data.source.provider_full_name
            },
            'projects_numb': cls.institution.nodes.filter(type='osf.node').count(),
            'files_numb': files_numb,
            'size': total_size,
            'file_path': cls.export_data.get_file_info_file_path()
        }
        cls.file_info_json = {
            'institution': cls.institution_json,
            'files': [{
                'id': file1.id,
                'path': file1.path,
                'materialized_path': file1.materialized_path,
                'name': file1.name,
                'provider': file1.provider,
                'created_at': file1.created.strftime('%Y-%m-%d %H:%M:%S'),
                'modified_at': file1.modified.strftime('%Y-%m-%d %H:%M:%S'),
                'project': {
                    'id': file1.target._id,
                    'name': file1.target.title,
                },
                'tags': [],
                'version': [{
                    'identifier': file_version.identifier,
                    'created_at': file_version.created.strftime('%Y-%m-%d %H:%M:%S'),
                    'modified_at': file_version.created.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': file_version.size,
                    'version_name': file_versions_through.version_name if file_versions_through else file1.name,
                    'contributor': file_version.creator.username,
                    'metadata': file_version.metadata,
                    'location': file_version.location,
                }],
                'size': 0,
                'location': file_version.location,
                'timestamp': {},
            }]
        }

    def test_init(self):
        nt.assert_is_not_none(self.export_data)
        nt.assert_equal(self.export_data.status, ExportData.STATUS_COMPLETED)

    def test_repr(self):
        expected_value = f'"({self.export_data.source}-{self.export_data.location})[{self.export_data.status}]"'
        nt.assert_equal(repr(self.export_data), expected_value)

    def test_str(self):
        expected_value = f'"({self.export_data.source}-{self.export_data.location})[{self.export_data.status}]"'
        nt.assert_equal(repr(self.export_data), expected_value)

    def test_extract_file_information_json_from_source_storage__00_not_institution(self):
        export_data = ExportDataFactory()
        result = export_data.extract_file_information_json_from_source_storage()
        nt.assert_is_none(result)

    def test_extract_file_information_json_from_source_storage__01_normal(self):
        test_file_info_json = copy.deepcopy(self.file_info_json)

        result = self.export_data.extract_file_information_json_from_source_storage()

        nt.assert_is_instance(result, tuple)
        export_data_json, file_info_json = result
        file_info_first_file = file_info_json.get('files', [{}])[0]
        test_file_info_file = test_file_info_json.get('files', [{}])[0]

        nt.assert_equal(export_data_json, self.export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_first_file.get('tags'), test_file_info_file.get('tags'))
        nt.assert_equal(file_info_first_file.get('version'), test_file_info_file.get('version'))
        nt.assert_equal(file_info_first_file.get('location'), test_file_info_file.get('location'))
        nt.assert_equal(file_info_first_file.get('timestamp'), test_file_info_file.get('timestamp'))

    def test_extract_file_information_json_from_source_storage__02_with_tags(self):
        # Add tags to file info JSON and test DB
        test_file_info_json = copy.deepcopy(self.file_info_json)
        test_file_info_json['files'][0]['tags'] = ['tag1', 'tag2']
        tag1 = TagFactory(name='tag1', system=False)
        tag2 = TagFactory(name='tag2', system=False)
        self.file1.tags.set([tag1, tag2])

        result = self.export_data.extract_file_information_json_from_source_storage()

        nt.assert_is_instance(result, tuple)
        export_data_json, file_info_json = result

        file_info_first_file = file_info_json.get('files', [{}])[0]
        test_file_info_file = test_file_info_json.get('files', [{}])[0]

        nt.assert_equal(export_data_json, self.export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_first_file.get('tags'), test_file_info_file.get('tags'))
        nt.assert_equal(file_info_first_file.get('version'), test_file_info_file.get('version'))
        nt.assert_equal(file_info_first_file.get('location'), test_file_info_file.get('location'))
        nt.assert_equal(file_info_first_file.get('timestamp'), test_file_info_file.get('timestamp'))

    def test_extract_file_information_json_from_source_storage__03_with_timestamp(self):
        # Add timestamp to file info JSON and test DB
        test_file_info_json = copy.deepcopy(self.file_info_json)
        timestamp = RdmFileTimestamptokenVerifyResultFactory(
            project_id=self.file1.target._id, file_id=self.file1._id)
        test_file_info_json['files'][0]['timestamp'] = {
            'timestamp_id': timestamp.id,
            'inspection_result_status': timestamp.inspection_result_status,
            'provider': timestamp.provider,
            'upload_file_modified_user': timestamp.upload_file_modified_user,
            'project_id': timestamp.project_id,
            'path': timestamp.path,
            'key_file_name': timestamp.key_file_name,
            'upload_file_created_user': timestamp.upload_file_created_user,
            'upload_file_size': timestamp.upload_file_size,
            'verify_file_size': timestamp.verify_file_size,
            'verify_user': timestamp.verify_user
        }

        result = self.export_data.extract_file_information_json_from_source_storage()

        nt.assert_is_instance(result, tuple)
        export_data_json, file_info_json = result

        file_info_first_file = file_info_json.get('files', [{}])[0]
        test_file_info_file = test_file_info_json.get('files', [{}])[0]

        nt.assert_equal(export_data_json, self.export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_first_file.get('tags'), test_file_info_file.get('tags'))
        nt.assert_equal(file_info_first_file.get('version'), test_file_info_file.get('version'))
        nt.assert_equal(file_info_first_file.get('location'), test_file_info_file.get('location'))
        nt.assert_equal(file_info_first_file.get('timestamp'), test_file_info_file.get('timestamp'))

    def test_extract_file_information_json_from_source_storage__04_inst_region(self):
        self.inst_region.name = 'inst'
        self.inst_region.save()
        test_file_info_json = copy.deepcopy(self.file_info_json)
        test_export_data_json = copy.deepcopy(self.export_data_json)
        test_export_data_json['projects_numb'] -= 1
        test_export_data_json['files_numb'] -= 1
        test_export_data_json['size'] -= self.file1.versions.first().size
        test_export_data_json['storage']['name'] = self.inst_region.name

        result = self.export_data.extract_file_information_json_from_source_storage()

        nt.assert_is_instance(result, tuple)
        export_data_json, file_info_json = result

        file_info_files = file_info_json.get('files',)

        nt.assert_equal(export_data_json, test_export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_files, [])

        self.inst_region.name = self.default_region.name
        self.inst_region.save()

    def test_extract_file_information_json_from_source_storage__99_abnormal_file_data(self):
        test_file_info_json = copy.deepcopy(self.file_info_json)
        test_export_data_json = copy.deepcopy(self.export_data_json)
        test_export_data_json['files_numb'] -= 1
        test_export_data_json['size'] -= self.file1.versions.first().size
        self.file1.deleted = datetime.now()
        self.file1.deleted_on = None
        self.file1.deleted_by_id = None
        self.file1.save()

        result = self.export_data.extract_file_information_json_from_source_storage()

        nt.assert_is_instance(result, tuple)
        export_data_json, file_info_json = result

        file_info_files = file_info_json.get('files',)

        nt.assert_equal(export_data_json, test_export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_files, [])

        self.file1.deleted = None
        self.file1.deleted_on = datetime.now()
        self.file1.deleted_by_id = None
        self.file1.save()

        result = self.export_data.extract_file_information_json_from_source_storage()

        nt.assert_is_instance(result, tuple)
        export_data_json, file_info_json = result

        file_info_files = file_info_json.get('files',)

        nt.assert_equal(export_data_json, test_export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_files, [])

        self.file1.deleted = None
        self.file1.deleted_on = None
        self.file1.deleted_by_id = AuthUserFactory()
        self.file1.save()

        result = self.export_data.extract_file_information_json_from_source_storage()

        nt.assert_is_instance(result, tuple)
        export_data_json, file_info_json = result

        file_info_files = file_info_json.get('files',)

        nt.assert_equal(export_data_json, test_export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_files, [])

        self.file1.deleted = None
        self.file1.deleted_on = None
        self.file1.deleted_by_id = None
        self.file1.save()

    def test_process_start_timestamp(self):
        nt.assert_equal(self.export_data.process_start_timestamp, self.export_data.process_start.strftime('%s'))

    def test_process_start_display(self):
        nt.assert_equal(self.export_data.process_start_display,
                        self.export_data.process_start.strftime('%Y%m%dT%H%M%S'))

    def test_export_data_folder_name(self):
        expected_value = 'export_{}_{}'.format(self.export_data.source.id, self.export_data.process_start_timestamp)
        nt.assert_equal(self.export_data.export_data_folder_name, expected_value)

    def test_export_data_folder_path(self):
        expected_value = '/export_{}_{}/'.format(self.export_data.source.id, self.export_data.process_start_timestamp)
        nt.assert_equal(self.export_data.export_data_folder_path, expected_value)

    def test_export_data_temp_file_path(self):
        res = self.export_data.export_data_temp_file_path
        nt.assert_greater(len(res), 0)

    def test_export_data_files_folder_path(self):
        res = self.export_data.export_data_files_folder_path
        nt.assert_greater(len(res), 0)

    def test_get_source_file_versions_min(self):
        file_info_json = dict(FAKE_DATA).copy()
        res = self.export_data.get_source_file_versions_min(file_info_json)
        nt.assert_greater(len(res), 0)

    def test_create_export_data_folder(self):
        mock_request = mock.MagicMock()
        mock_request.put.return_value = JsonResponse({'message': ''}, status=201)
        cookie = 'fake_cookie'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.create_export_data_folder(cookie)
        nt.assert_equal(res.status_code, 201)

    def test_delete_export_data_folder(self):
        mock_request = mock.MagicMock()
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        cookie = 'fake_cookie'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.delete_export_data_folder(cookie)
        nt.assert_equal(res.status_code, 204)

    def test_delete_export_data_file_from_location(self):
        mock_request = mock.MagicMock()
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        cookie = 'fake_cookie'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.delete_export_data_file_from_location(cookie)
        nt.assert_equal(res.status_code, 204)

    def test_delete_file_info_file_from_location(self):
        mock_request = mock.MagicMock()
        mock_request.delete.return_value = JsonResponse({'message': ''}, status=204)
        cookie = 'fake_cookie'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.delete_file_info_file_from_location(cookie)
        nt.assert_equal(res.status_code, 204)

    def test_create_export_data_files_folder(self):
        mock_request = mock.MagicMock()
        mock_request.put.return_value = JsonResponse({'message': ''}, status=201)
        cookie = 'fake_cookie'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.create_export_data_files_folder(cookie)
        nt.assert_equal(res.status_code, 201)

    def test_read_file_info_from_location(self):
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.read_file_info_from_location(cookie)
        nt.assert_equal(res.status_code, 200)

    def test_read_export_data_from_location(self):
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.read_export_data_from_location(cookie)
        nt.assert_equal(res.status_code, 200)

    def test_upload_export_data_file(self):
        mock_request = mock.MagicMock()
        mock_request.put.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        file_path = 'admin/base/schemas/export-data-schema.json'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.upload_export_data_file(cookie, file_path)
        nt.assert_equal(res.status_code, 200)

    def test_read_data_file_from_source(self):
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        project_id = 100
        provider = 'osfstorage'
        file_path = '/fake_path'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.read_data_file_from_source(cookie, project_id, provider, file_path)
        nt.assert_equal(res.status_code, 200)

    def test_get_data_file_file_path(self):
        file_path = '/fake_path'
        res = self.export_data.get_data_file_file_path(file_path)
        nt.assert_greater(len(res), 0)

    def test_read_data_file_from_location(self):
        mock_request = mock.MagicMock()
        mock_request.get.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        file_path = '/fake_path'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.read_data_file_from_location(cookie, file_path)
        nt.assert_equal(res.status_code, 200)

    def test_transfer_export_data_file_to_location(self):
        mock_request = mock.MagicMock()
        mock_request.put.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        provider = 'osfstorage'
        file_path = '/fake_path'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.transfer_export_data_file_to_location(cookie, provider, file_path)
        nt.assert_equal(res.status_code, 200)

    def test_copy_export_data_file_to_location(self):
        mock_request = mock.MagicMock()
        mock_request.post.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        project_id = 'project_id_1'
        provider = 'osfstorage'
        file_path = '/fake_path'
        file_name = 'file_name'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.copy_export_data_file_to_location(cookie, project_id, provider, file_path, file_name)
        nt.assert_equal(res.status_code, 200)

    def test_upload_file_info_file(self):
        mock_request = mock.MagicMock()
        mock_request.put.return_value = JsonResponse({'message': ''}, status=200)
        cookie = 'fake_cookie'
        file_path = 'admin/base/schemas/export-data-schema.json'
        with mock.patch('osf.models.export_data.requests', mock_request):
            res = self.export_data.upload_file_info_file(cookie, file_path)
        nt.assert_equal(res.status_code, 200)

    def test_get_export_data_file_path(self):
        res = self.export_data.get_export_data_file_path()
        nt.assert_greater(len(res), 0)

    def test_get_export_data_filename(self):
        res = self.export_data.get_export_data_filename()
        expected_value = 'export_data_{}_{}.json'.format(self.export_data.source.guid,
                                                         self.export_data.process_start_timestamp)
        nt.assert_equal(res, expected_value)

    def test_get_file_info_filename(self):
        res = self.export_data.get_file_info_filename()
        expected_value = 'file_info_{}_{}.json'.format(self.export_data.source.guid,
                                                       self.export_data.process_start_timestamp)
        nt.assert_equal(res, expected_value)


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestExportDataWithRestoreData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.export_data = ExportDataFactory()
        cls.institution = InstitutionFactory.create(_id='vcu')
        cls.institution_json = {
            'id': cls.institution.id,
            'guid': cls.institution.guid,
            'name': cls.institution.name
        }
        cls.export_data_json = {
            'institution': cls.institution_json,
            'process_start': '1231',
            'process_end': '1231231',
            'storage': {
                'name': 'abc',
                'type': 'bcd'
            },
            'projects_numb': 0,
            'files_numb': 0,
            'size': 0,
            'file_path': None
        }
        cls.file_info_json = {
            'institution': cls.institution_json,
            'files': []
        }
        cls.export_data_restore = ExportDataRestoreFactory(export=cls.export_data)

    def test_get_all_restored(self):
        nt.assert_equal(self.export_data.get_all_restored().first(), self.export_data_restore)

    def test_has_restored(self):
        nt.assert_equal(self.export_data.has_restored(), True)

    def test_get_latest_restored(self):
        nt.assert_equal(self.export_data.get_latest_restored(), self.export_data_restore)

    def test_get_latest_restored_data_with_destination_id(self):
        destination_id = self.export_data_restore.destination.id
        nt.assert_equal(self.export_data.get_latest_restored_data_with_destination_id(destination_id),
                        self.export_data_restore)


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestDateTruncMixin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.date_mixin = DateTruncMixin()

    def test_truncate_date(self):
        fake_data = 'fake_value'
        res = self.date_mixin.truncate_date(fake_data)
        nt.assert_equal(res, fake_data)
