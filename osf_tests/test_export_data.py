import mock
import pytest
from datetime import datetime
from django.http import JsonResponse
from django.test import TestCase
from nose import tools as nt

from addons.osfstorage.models import Region
from addons.osfstorage.settings import DEFAULT_REGION_ID
from addons.osfstorage.tests.factories import FileVersionFactory
from osf.models import AbstractNode
from osf.models.export_data import DateTruncMixin
from osf_tests.factories import (
    ExportDataFactory,
    InstitutionFactory,
    ProjectFactory,
    OsfStorageFileFactory,
    RdmFileTimestamptokenVerifyResultFactory,
    BaseFileVersionsThroughFactory,
    ExportDataRestoreFactory,
    RegionFactory,
    bulkmount_waterbutler_settings,
)

FAKE_DATA = {
    'institution': {
        'id': 66,
        'guid': 'wustl',
        'name': 'Washington University in St. Louis [Test]'
    },
    'files': [
        {
            'id': 1733,
            'path': '/631879ebb71d8f1ae01f4c10',
            'materialized_path': '/nii/ember-animated/-private/sprite.d.ts',
            'name': 'sprite.d.ts',
            'provider': 'osfstorage',
            'created_at': '2022-09-07 11:00:59',
            'modified_at': '2022-09-07 11:00:59',
            'project': {
                'id': 'wh6za',
                'name': 'Project C0001'
            },
            'tags': [],
            'version': [
                {
                    'identifier': '1',
                    'created_at': '2022-09-07 11:00:59',
                    'size': 150,
                    'version_name': 'sprite.d.ts',
                    'contributor': 'user001@example.com.vn',
                    'metadata': {
                        'md5': 'ad85d0c3911f56d671cc41c952fa96b2',
                        'etag': 'cdb490b21480b381d118b303468d1fb225ad6d1f16e5f096262a8ea0835d4399',
                        'kind': 'file',
                        'name': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'path': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha1': '2f1e64c37f30d1c35e3c0e7b68650b1e8e1c05dc',
                        'size': 150,
                        'extra': {},
                        'sha256': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'sha512': '6f2617c63ee21b7acf1b87db92faba2677e62638a0831708d2e9ad01fe46d17f231232',
                        'sizeInt': 150,
                        'modified': 'Fri, 12 Aug 2022 11:21:52 +0000',
                        'provider': 'filesystem',
                        'contentType': '',
                        'created_utc': '',
                        'materialized': '/f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'modified_utc': '2022-08-12T11:21:52.989761+00:00'
                    },
                    'location': {
                        'host': 'de222e410dd7',
                        'folder': '/code/website/osfstoragecache',
                        'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                        'address': '',
                        'service': 'filesystem',
                        'version': '0.0.1',
                        'provider': 'filesystem'
                    }
                },
            ],
            'size': 150,
            'location': {
                'host': 'de222e410dd7',
                'folder': '/code/website/osfstoragecache',
                'object': 'f4ddb7e6109eac566cd6d7cb29faa40f4e3b92b202e21863a309b7eb87543b67',
                'address': '',
                'service': 'filesystem',
                'version': '0.0.1',
                'provider': 'filesystem'
            },
            'timestamp': {}
        },
    ]
}


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestExportData(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.export_data = ExportDataFactory()
        cls.institution = InstitutionFactory.create(_id='vcu')
        project = ProjectFactory()
        cls.institution = InstitutionFactory.create(_id=cls.export_data.source.guid)
        cls.institution.nodes.set([project])
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
            'projects_numb': 1,
            'files_numb': 1,
            'size': -1,
            'file_path': None
        }

        projects = cls.institution.nodes.filter(type='osf.node')
        projects__ids = projects.values_list('id', flat=True)
        object_id = projects__ids[0]
        target = AbstractNode(id=object_id)
        node = OsfStorageFileFactory.create(target_object_id=object_id, target=target)
        file_version = FileVersionFactory(region=cls.export_data.source)
        file_version.creator.affiliated_institutions.set([cls.institution])

        file_versions_through = BaseFileVersionsThroughFactory.create(version_name='file.txt', basefilenode=node,
                                                                      fileversion=file_version)
        cls.file_info_json = {
            'institution': cls.institution_json,
            'files': [{
                'id': node.id,
                'path': node.path,
                'materialized_path': node.materialized_path,
                'name': node.name,
                'provider': node.provider,
                'created_at': node.created.strftime('%Y-%m-%d %H:%M:%S'),
                'modified_at': node.modified.strftime('%Y-%m-%d %H:%M:%S'),
                'project': {
                    'id': node.target._id,
                    'name': node.target.title,
                },
                'tags': [],
                'version': [{
                    'identifier': file_version.identifier,
                    'created_at': file_version.created.strftime('%Y-%m-%d %H:%M:%S'),
                    'size': file_version.size,
                    'version_name': file_versions_through.version_name if file_versions_through else node.name,
                    'contributor': file_version.creator.username,
                    'metadata': file_version.metadata,
                    'location': file_version.location,
                }],
                'size': 0,
                'location': file_version.location,
                'timestamp': {},
            }]
        }
        cls.file = node

    def test_repr(self):
        expected_value = '"({}-{})[{}]"'.format(self.export_data.source, self.export_data.location, self.export_data.status)
        nt.assert_equal(repr(self.export_data), expected_value)

    def test_process_start_timestamp(self):
        res = self.export_data.process_start_timestamp
        nt.assert_greater(len(res), 0)

    def test_process_start_display(self):
        res = self.export_data.process_start_display
        nt.assert_greater(len(res), 0)

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

    def test_extract_file_information_json_from_source_storage(self):
        mock_obj = mock.MagicMock()
        mock_obj.filter.return_value.first.return_value = RdmFileTimestamptokenVerifyResultFactory(
            project_id=self.file.target.id, file_id=self.file.id)
        with mock.patch('osf.models.export_data.RdmFileTimestamptokenVerifyResult.objects', mock_obj):
            result = self.export_data.extract_file_information_json_from_source_storage()
        nt.assert_is_not_none(result)

    def test_extract_file_information_json_from_source_storage_with_default_storage_project(self):
        region = RegionFactory(waterbutler_settings=bulkmount_waterbutler_settings)
        export_data = ExportDataFactory(source=region)
        project = ProjectFactory()
        institution = InstitutionFactory.create(_id=export_data.source.guid)
        institution.nodes.set([project])
        default_region = Region.objects.get(_id=DEFAULT_REGION_ID)
        file_version = FileVersionFactory(region=default_region)
        file_version.creator.affiliated_institutions.set([institution])
        object_id = project.id
        target = AbstractNode(id=object_id)
        node = OsfStorageFileFactory.create(name='file2.txt', created=datetime.now(), target_content_type=self.file.target_content_type,
                                            target_object_id=object_id, target=target)
        BaseFileVersionsThroughFactory.create(version_name='file2.txt', basefilenode=node, fileversion=file_version)

        mock_obj = mock.MagicMock()
        mock_obj.filter.return_value.first.return_value = RdmFileTimestamptokenVerifyResultFactory(
            project_id=self.file.target.id, file_id=self.file.id)
        with mock.patch('osf.models.export_data.RdmFileTimestamptokenVerifyResult.objects', mock_obj):
            result = export_data.extract_file_information_json_from_source_storage()
        nt.assert_is_not_none(result)

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
        expected_value = 'export_data_{}_{}.json'.format(self.export_data.source.guid, self.export_data.process_start_timestamp)
        nt.assert_equal(res, expected_value)

    def test_get_file_info_filename(self):
        res = self.export_data.get_file_info_filename()
        expected_value = 'file_info_{}_{}.json'.format(self.export_data.source.guid, self.export_data.process_start_timestamp)
        nt.assert_equal(res, expected_value)

    def test_extract_file_information_json_from_source_storage_not_institution(self):
        mock_obj = mock.MagicMock()
        mock_obj.load.return_value = None
        with mock.patch('osf.models.export_data.Institution', mock_obj):
            result = self.export_data.extract_file_information_json_from_source_storage()
        nt.assert_is_none(result)


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
        nt.assert_equal(self.export_data.get_latest_restored_data_with_destination_id(destination_id), self.export_data_restore)


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
