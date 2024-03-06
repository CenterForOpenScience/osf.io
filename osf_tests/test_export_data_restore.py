import copy
from datetime import datetime

import pytest
import requests
from addons.osfstorage.tests.factories import FileVersionFactory
from django.test import TestCase
from mock import patch
from nose import tools as nt
from rest_framework import status

from addons.osfstorage.models import Region
from addons.osfstorage.settings import DEFAULT_REGION_ID
from osf.models import AbstractNode, ExportData
from osf_tests.factories import (
    TagFactory,
    RegionFactory,
    ProjectFactory,
    AuthUserFactory,
    InstitutionFactory,
    OsfStorageFileFactory,
    ExportDataRestoreFactory,
    BaseFileVersionsThroughFactory,
    RdmFileTimestamptokenVerifyResultFactory,
)


@pytest.mark.feature_202210
@pytest.mark.django_db
class TestExportDataRestore(TestCase):

    @classmethod
    def setUpTestData(cls):
        default_region = Region.objects.get(_id=DEFAULT_REGION_ID)
        inst_region = RegionFactory(
            name=default_region.name,
            waterbutler_credentials=default_region.waterbutler_credentials,
            waterbutler_settings=default_region.waterbutler_settings
        )
        cls.institution = InstitutionFactory.create(_id=inst_region.guid)
        cls.data_restore = ExportDataRestoreFactory(destination=inst_region)
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
            'process_start': cls.data_restore.process_start.strftime('%Y-%m-%d %H:%M:%S'),
            'process_end': cls.data_restore.process_end.strftime(
                '%Y-%m-%d %H:%M:%S') if cls.data_restore.process_end else None,
            'storage': {
                'name': cls.data_restore.destination.name,
                'type': cls.data_restore.destination.provider_full_name
            },
            'projects_numb': cls.institution.nodes.filter(type='osf.node').count(),
            'files_numb': files_numb,
            'size': total_size,
            'file_path': None
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
        nt.assert_is_not_none(self.data_restore)
        nt.assert_equal(self.data_restore.status, ExportData.STATUS_COMPLETED)

    def test_repr(self):
        test_repr = f'"({self.data_restore.export}-{self.data_restore.destination})[{self.data_restore.status}]"'
        nt.assert_equal(repr(self.data_restore), test_repr)

    def test_str(self):
        test_str = f'"({self.data_restore.export}-{self.data_restore.destination})[{self.data_restore.status}]"'
        nt.assert_equal(str(self.data_restore), test_str)

    def test_extract_file_information_json_from_destination_storage__00_not_institution(self):
        export_data_restore = ExportDataRestoreFactory.build()
        result = export_data_restore.extract_file_information_json_from_destination_storage()
        nt.assert_is_none(result)

    def test_extract_file_information_json_from_destination_storage__01_normal(self):
        test_file_info_json = copy.deepcopy(self.file_info_json)

        result = self.data_restore.extract_file_information_json_from_destination_storage()

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

    def test_extract_file_information_json_from_destination_storage__02_with_tags(self):
        # Add tags to file info JSON and test DB
        test_file_info_json = copy.deepcopy(self.file_info_json)
        test_file_info_json['files'][0]['tags'] = ['tag1', 'tag2']
        tag1 = TagFactory(name='tag1', system=False)
        tag2 = TagFactory(name='tag2', system=False)
        self.file1.tags.set([tag1, tag2])

        result = self.data_restore.extract_file_information_json_from_destination_storage()

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

    def test_extract_file_information_json_from_destination_storage__03_with_timestamp(self):
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

        result = self.data_restore.extract_file_information_json_from_destination_storage()

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

    def test_extract_file_information_json_from_sourFce_storage__04_abnormal_file_data(self):
        test_file_info_json = copy.deepcopy(self.file_info_json)
        test_export_data_json = copy.deepcopy(self.export_data_json)
        test_export_data_json['projects_numb'] -= 1
        test_export_data_json['files_numb'] -= 1
        test_export_data_json['size'] -= self.file1.versions.first().size
        self.file1.deleted = datetime.now()
        self.file1.deleted_on = None
        self.file1.deleted_by_id = None
        self.file1.save()

        result = self.data_restore.extract_file_information_json_from_destination_storage()

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

        result = self.data_restore.extract_file_information_json_from_destination_storage()

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

        result = self.data_restore.extract_file_information_json_from_destination_storage()

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
        nt.assert_equal(self.data_restore.process_start_timestamp, self.data_restore.process_start.strftime('%s'))

    def test_process_start_display(self):
        nt.assert_equal(self.data_restore.process_start_display,
                        self.data_restore.process_start.strftime('%Y%m%dT%H%M%S'))

    @patch(f'requests.put')
    def test_transfer_export_data_file_to_destination(self, mock_request):
        test_response = requests.Response()
        test_response.status_code = status.HTTP_200_OK
        mock_request.return_value = test_response
        response = self.data_restore.transfer_export_data_file_to_destination(None, 'test1', 'osfstorage', '/',
                                                                              'file1.txt', {})
        nt.assert_equal(response, test_response)

    def test_update(self):
        current_datetime = datetime.now()
        self.data_restore.update(process_end=current_datetime)
        nt.assert_equal(self.data_restore.process_end, current_datetime)
