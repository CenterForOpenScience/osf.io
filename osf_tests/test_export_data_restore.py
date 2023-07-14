import copy
from datetime import datetime

import pytest
import requests
from django.test import TestCase
from mock import patch
from nose import tools as nt
from rest_framework import status

from addons.osfstorage.tests.factories import FileVersionFactory
from osf.models import AbstractNode, ExportData
from osf_tests.factories import (
    TagFactory,
    ProjectFactory,
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
        cls.data_restore = ExportDataRestoreFactory()
        project = ProjectFactory()
        cls.institution = InstitutionFactory.create(_id=cls.data_restore.destination.guid)
        cls.institution.nodes.set([project])
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
        file_version = FileVersionFactory(region=cls.data_restore.destination)
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
                    'modified_at': file_version.created.strftime('%Y-%m-%d %H:%M:%S'),
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

    def test_init(self):
        nt.assert_is_not_none(self.data_restore)
        nt.assert_equal(self.data_restore.status, ExportData.STATUS_COMPLETED)

    def test_repr(self):
        test_repr = f'"({self.data_restore.export}-{self.data_restore.destination})[{self.data_restore.status}]"'
        nt.assert_equal(repr(self.data_restore), test_repr)

    def test_str(self):
        test_str = f'"({self.data_restore.export}-{self.data_restore.destination})[{self.data_restore.status}]"'
        nt.assert_equal(str(self.data_restore), test_str)

    def test_extract_file_information_json_from_destination_storage(self):
        test_file_info_json = copy.deepcopy(self.file_info_json)

        result = self.data_restore.extract_file_information_json_from_destination_storage()

        nt.assert_is_not_none(result)
        export_data_json, file_info_json = result
        file_info_first_file = file_info_json.get('files', [{}])[0]
        test_file_info_file = test_file_info_json.get('files', [{}])[0]

        nt.assert_equal(export_data_json, self.export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_first_file.get('tags'), test_file_info_file.get('tags'))
        nt.assert_equal(file_info_first_file.get('version'), test_file_info_file.get('version'))
        nt.assert_equal(file_info_first_file.get('location'), test_file_info_file.get('location'))
        nt.assert_equal(file_info_first_file.get('timestamp'), test_file_info_file.get('timestamp'))

    def test_extract_file_information_json_from_destination_storage_institution_not_found(self):
        export_data_restore_without_institution = ExportDataRestoreFactory.build()
        result = export_data_restore_without_institution.extract_file_information_json_from_destination_storage()
        nt.assert_is_none(result)

    def test_extract_file_information_json_from_destination_storage_with_tags(self):
        # Add tags to file info JSON and test DB
        test_file_info_json = copy.deepcopy(self.file_info_json)
        test_file_info_json['files'][0]['tags'] = ['tag1', 'tag2']
        tag1 = TagFactory(name='tag1', system=False)
        tag2 = TagFactory(name='tag2', system=False)
        self.file.tags.set([tag1, tag2])

        result = self.data_restore.extract_file_information_json_from_destination_storage()

        nt.assert_is_not_none(result)

        export_data_json, file_info_json = result
        file_info_first_file = file_info_json.get('files', [{}])[0]
        test_file_info_file = test_file_info_json.get('files', [{}])[0]

        nt.assert_equal(export_data_json, self.export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_first_file.get('tags'), test_file_info_file.get('tags'))
        nt.assert_equal(file_info_first_file.get('version'), test_file_info_file.get('version'))
        nt.assert_equal(file_info_first_file.get('location'), test_file_info_file.get('location'))
        nt.assert_equal(file_info_first_file.get('timestamp'), test_file_info_file.get('timestamp'))

    def test_extract_file_information_json_from_destination_storage_with_timestamp(self):
        # Add timestamp to file info JSON and test DB
        test_file_info_json = copy.deepcopy(self.file_info_json)
        timestamp = RdmFileTimestamptokenVerifyResultFactory(
            project_id=self.file.target._id, file_id=self.file._id)
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

        nt.assert_is_not_none(result)
        export_data_json, file_info_json = result
        file_info_first_file = file_info_json.get('files', [{}])[0]
        test_file_info_file = test_file_info_json.get('files', [{}])[0]

        nt.assert_equal(export_data_json, self.export_data_json)
        nt.assert_equal(file_info_json.get('institution'), test_file_info_json.get('institution'))
        nt.assert_equal(file_info_first_file.get('tags'), test_file_info_file.get('tags'))
        nt.assert_equal(file_info_first_file.get('version'), test_file_info_file.get('version'))
        nt.assert_equal(file_info_first_file.get('location'), test_file_info_file.get('location'))
        nt.assert_equal(file_info_first_file.get('timestamp'), test_file_info_file.get('timestamp'))

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
