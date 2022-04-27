# -*- coding: utf-8 -*-
import datetime
import mock
from nose.tools import *  # noqa (PEP8 asserts)
import pytest
from addons.osfstorage.models import OsfStorageFileNode
from api.base import settings as api_settings
from tests.base import OsfTestCase
from osf.models import (
    FileLog, FileInfo, TrashedFileNode, TrashedFolder, UserQuota, ProjectStorageType, BaseFileNode
)
from osf_tests.factories import (
    ProjectFactory, UserFactory, InstitutionFactory, RegionFactory
)
from website.util import quota
from api.base import settings as api_settings


@pytest.mark.skip('Clone test case from tests/test_quota.py for making coverage')
class TestSaveUsedQuota(OsfTestCase):
    def setUp(self):
        super(TestSaveUsedQuota, self).setUp()
        self.user = UserFactory()
        self.project_creator = UserFactory()
        self.node = ProjectFactory(creator=self.project_creator)
        self.file = OsfStorageFileNode.create(
            target=self.node,
            path='/testfile',
            _id='testfile',
            name='testfile',
            materialized_path='/testfile'
        )
        self.file.save()
        self.base_file_node = BaseFileNode(type='osf.s3file', provider='s3', _path='/testfile',
                _materialized_path='/testfile', target_object_id=self.node.id, target_content_type_id=2)
        self.base_folder_node = BaseFileNode(type='osf.s3folder', provider='s3', _path='/testfolder',
                _materialized_path='/testfolder', target_object_id=self.node.id, target_content_type_id=2)


    def test_add_first_file_custom_storage(self):
        assert_false(UserQuota.objects.filter(user=self.project_creator).exists())

        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        RegionFactory(_id=institution._id)
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_ADDED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': '/' + self.file._id,
                    'kind': 'file',
                    'size': 1200,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '1'}
                }
            }
        )

        user_quota = UserQuota.objects.filter(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        ).all()
        assert_equal(len(user_quota), 1)
        user_quota = user_quota[0]
        assert_equal(user_quota.used, 1200)

    def test_add_file(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_ADDED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1000,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '1'}
                }
            }
        )

        user_quota = UserQuota.objects.filter(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        ).all()
        assert_equal(len(user_quota), 1)
        user_quota = user_quota[0]
        assert_equal(user_quota.used, 6500)

    def test_add_file_custom_storage(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )

        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        RegionFactory(_id=institution._id)
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_ADDED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1200,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '1'}
                }
            }
        )

        user_quota = UserQuota.objects.filter(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        ).all()
        assert_equal(len(user_quota), 1)
        user_quota = user_quota[0]
        assert_equal(user_quota.used, 6700)

    def test_add_file_negative_size(self):
        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_ADDED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': -1000,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '1'}
                }
            }
        )
        assert_false(UserQuota.objects.filter(user=self.project_creator).exists())

    def test_delete_file(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        FileInfo.objects.create(file=self.file, file_size=1000)

        self.file.deleted_on = datetime.datetime.now()
        self.file.deleted_by = self.user
        self.file.type = 'osf.trashedfile'
        self.file.save()

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'extra': {}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 4500)

    def test_delete_file_custom_storage(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        FileInfo.objects.create(file=self.file, file_size=1200)

        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        RegionFactory(_id=institution._id)
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )

        self.file.deleted_on = datetime.datetime.now()
        self.file.deleted_by = self.user
        self.file.type = 'osf.trashedfile'
        self.file.save()

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'extra': {}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 4300)

    def test_delete_file_lower_used_quota(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=500
        )
        FileInfo.objects.create(file=self.file, file_size=1000)

        self.file.deleted_on = datetime.datetime.now()
        self.file.deleted_by = self.user
        self.file.type = 'osf.trashedfile'
        self.file.save()

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'extra': {}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 0)

    @mock.patch('website.util.quota.logging')
    def test_delete_file_invalid_file(self, mock_logging):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': 'malicioususereditedthis',
                    'kind': 'file',
                    'extra': {}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 5500)
        mock_logging.error.assert_called_with('FileNode not found, cannot update used quota!')

    @mock.patch('website.util.quota.logging')
    def test_delete_file_without_fileinfo(self, mock_logging):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )

        self.file.deleted_on = datetime.datetime.now()
        self.file.deleted_by = self.user
        self.file.type = 'osf.trashedfile'
        self.file.save()

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'extra': {}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 5500)
        mock_logging.error.assert_called_with('FileInfo not found, cannot update used quota!')

    @mock.patch('website.util.quota.logging')
    def test_delete_file_not_trashed(self, mock_logging):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        FileInfo.objects.create(file=self.file, file_size=1000)

        self.file.deleted_on = datetime.datetime.now()
        self.file.deleted_by = self.user
        self.file.save()

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'extra': {}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 5500)
        mock_logging.error.assert_called_with('FileNode is not trashed, cannot update used quota!')

    def test_delete_file_without_userquota(self):
        FileInfo.objects.create(file=self.file, file_size=1000)

        self.file.deleted_on = datetime.datetime.now()
        self.file.deleted_by = self.user
        self.file.type = 'osf.trashedfile'
        self.file.save()

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'extra': {}
                }
            }
        )

        assert_false(UserQuota.objects.filter(user=self.project_creator).exists())

    def test_delete_folder(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )

        folder1 = TrashedFolder(
            target=self.node,
            name='testfolder',
            deleted_on=datetime.datetime.now(),
            deleted_by=self.user
        )
        folder1.save()
        folder2 = TrashedFolder(
            target=self.node,
            name='testfolder',
            parent_id=folder1.id,
            deleted_on=datetime.datetime.now(),
            deleted_by=self.user
        )
        folder2.save()
        file1 = TrashedFileNode.create(
            target=self.node,
            name='testfile1',
            parent_id=folder1.id,
            deleted_on=datetime.datetime.now(),
            deleted_by=self.user
        )
        file1.provider = 'osfstorage'
        file1.save()
        file2 = TrashedFileNode.create(
            target=self.node,
            name='testfile2',
            parent_id=folder2.id,
            deleted_on=datetime.datetime.now(),
            deleted_by=self.user
        )
        file2.provider = 'osfstorage'
        file2.save()

        file1_info = FileInfo(file=file1, file_size=2000)
        file1_info.save()
        file2_info = FileInfo(file=file2, file_size=3000)
        file2_info.save()

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_REMOVED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfolder',
                    'materialized': '/testfolder',
                    'path': '{}/'.format(folder1._id),
                    'kind': 'folder',
                    'extra': {}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 500)

    def test_edit_file(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        FileInfo.objects.create(file=self.file, file_size=1000)

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_UPDATED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1500,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '2'}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 6000)

    def test_edit_file_custom_storage(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        FileInfo.objects.create(file=self.file, file_size=1000)

        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        RegionFactory(_id=institution._id)
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_UPDATED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1700,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '2'}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 6200)

    def test_edit_file_negative_size(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        FileInfo.objects.create(file=self.file, file_size=1000)

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_UPDATED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': -1500,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '2'}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 5500)

    def test_edit_file_without_fileinfo(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_UPDATED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1500,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '2'}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 7000)

    def test_edit_file_lower_used_quota(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=500
        )
        FileInfo.objects.create(file=self.file, file_size=3000)

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_UPDATED,
            payload={
                'provider': 'osfstorage',
                'metadata': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 2000,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '2'}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 0)

    def test_add_file_when_not_osfstorage(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.NII_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )

        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_ADDED,
            payload={
                'provider': 'github',
                'metadata': {
                    'provider': 'github',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1000,
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '1'}
                }
            }
        )

        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.NII_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 5500)

    def test_move_file(self):
        quota.update_used_quota(
            self=None,
            target=self.node,
            user=self.user,
            event_type=FileLog.FILE_ADDED,
            payload={
                'metadata': {
                    'created_utc': '',
                    'modified_utc': '',
                    'extra': {'version': '1'}
                },
                'source': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1000,
                    'extra': {'version': '1'}
                },
                'destination': {
                    'provider': 'osfstorage',
                    'name': 'testfile',
                    'materialized': '/filename',
                    'path': self.file._id,
                    'kind': 'file',
                    'size': 1000,
                    'extra': {'version': '1'}
                }
            }
        )

    def test_rename_folder_with_AmazonS3(self):
        mock_base_file_node = mock.MagicMock()
        mock_base_file_node_orderby = mock.MagicMock()
        mock_base_file_node.objects.filter.return_value = [BaseFileNode(type='osf.s3folder', provider='s3', _path='/newfoldername',
                _materialized_path='/newfoldername', target_object_id=self.node.id, target_content_type_id=2)]
        mock_base_file_node_orderby.filter.return_value.order_by.return_value.first.return_value = BaseFileNode(type='osf.s3folder', provider='s3', _path='/newfoldername',
                _materialized_path='/newfoldername', target_object_id=self.node.id, target_content_type_id=2)

        with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node):
            with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node_orderby):
                quota.update_used_quota(
                    self=None,
                    target=self.node,
                    user=self.user,
                    event_type=FileLog.FILE_RENAMED,
                    payload={
                        'destination': {
                            'provider': 's3',
                            'path': '/newfoldername',
                            'kind': 'folder',
                        },
                        'source': {
                            'provider': 's3',
                            'path': '/prefolderename',
                            'kind': 'folder',
                        },
                    }
                )

    def test_rename_file_with_AmazonS3(self):
        mock_base_file_node = mock.MagicMock()
        mock_base_file_node_orderby = mock.MagicMock()
        mock_base_file_node.objects.filter.return_value = [BaseFileNode(type='osf.s3file', provider='s3', _path='/newfilename',
                _materialized_path='/newfilename', target_object_id=self.node.id, target_content_type_id=2)]
        mock_base_file_node_orderby.filter.return_value.order_by.return_value.first.return_value = BaseFileNode(type='osf.s3file', provider='s3', _path='/newfilename',
                _materialized_path='/newfilename', target_object_id=self.node.id, target_content_type_id=2)

        with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node):
            with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node_orderby):
                quota.update_used_quota(
                    self=None,
                    target=self.node,
                    user=self.user,
                    event_type=FileLog.FILE_RENAMED,
                    payload={
                        'destination': {
                            'provider': 's3',
                            'path': '/newfilename',
                            'kind': 'file',
                        },
                        'source': {
                            'provider': 's3',
                            'path': '/prefilename',
                            'kind': 'file',
                        },
                    }
                )

    def test_upload_file_with_Amazon_S3(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5000
        )

        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        RegionFactory(_id=institution._id)
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )
        mock_base_file_node = mock.MagicMock()
        mock_file_info = mock.MagicMock()
        mock_base_file_node.objects.filter.return_value.order_by.return_value.first.return_value = BaseFileNode(type='osf.s3file', provider='s3', _path='/testfile',
                _materialized_path='/testfile', parent_id=self.node.id, target_object_id=self.node.id, target_content_type_id=2)
        mock_file_info.objects.create.return_value = None

        with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node):
            with mock.patch('website.util.quota.FileInfo', mock_file_info):
                quota.update_used_quota(
                    self=None,
                    target=self.node,
                    user=self.user,
                    event_type=FileLog.FILE_ADDED,
                    payload={
                        'provider': 's3',
                        'metadata': {
                            'provider': 's3',
                            'name': 'testfile',
                            'materialized': '/testfile',
                            'path': '/testfile',
                            'kind': 'file',
                            'size': 2000,
                        }
                    }
                )

        user_quota = UserQuota.objects.filter(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        ).all()
        assert_equal(len(user_quota), 1)
        user_quota = user_quota[0]
        assert_equal(user_quota.used, 7000)

    def test_add_folder_with_Amazon_S3(self):
        UserQuota.objects.create(
            user=self.project_creator,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5000
        )
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        RegionFactory(_id=institution._id)
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )
        mock_base_file_node = mock.MagicMock()
        mock_file_info = mock.MagicMock()
        mock_base_file_node.return_value = BaseFileNode(type='osf.s3folder', provider='s3', _path='/testfolder',
                _materialized_path='/testfolder', target_object_id=self.node.id, target_content_type_id=2)
        mock_base_file_node.objects.filter.return_value.order_by.return_value.first.return_value = BaseFileNode(type='osf.s3folder', provider='s3', _path='/testfolder',
                _materialized_path='/testfolder', target_object_id=self.node.id, target_content_type_id=2)
        mock_file_info.objects.create.return_value = None

        with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node):
            with mock.patch('website.util.quota.FileInfo', mock_file_info):
                quota.update_used_quota(
                    self=None,
                    target=self.node,
                    user=self.user,
                    event_type=FileLog.FILE_ADDED,
                    payload={
                        'provider': 's3',
                        'action': 'create_folder',
                        'metadata': {
                            'provider': 's3',
                            'name': '/testfolder',
                            'materialized': '/testfolder',
                            'path': '/testfolder',
                            'kind': 'folder',
                            'size': 0,
                        }
                    }
                )

        user_quota = UserQuota.objects.filter(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        ).all()
        assert_equal(len(user_quota), 1)
        user_quota = user_quota[0]
        assert_equal(user_quota.used, 5000)

    def test_delete_file_with_Amazon_S3(self):
        mock_base_file_node = mock.MagicMock()
        mock_file_info = mock.MagicMock()
        mock_user_quota = mock.MagicMock()
        mock_base_file_node.objects.filter.return_value.order_by.return_value.first.return_value = self.base_file_node
        mock_file_info.objects.get.return_value = FileInfo(file=self.base_file_node, file_size=1000)
        mock_user_quota.objects.filter.return_value.first.return_value = UserQuota(
            user=self.project_creator,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node):
            with mock.patch('website.util.quota.FileInfo', mock_file_info):
                with mock.patch('website.util.quota.UserQuota', mock_user_quota):
                    quota.update_used_quota(
                        self=None,
                        target=self.node,
                        user=self.user,
                        event_type=FileLog.FILE_REMOVED,
                        payload={
                            'provider': 's3',
                            'metadata': {
                                'provider': 's3',
                                'name': 'testfile',
                                'materialized': '/filename',
                                'path': '/filename',
                                'kind': 'file'
                            }
                        }
                    )
        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 4500)

    def test_delete_folder_with_Amazon_S3(self):
        mock_base_file_node = mock.MagicMock()
        mock_file_info = mock.MagicMock()
        mock_user_quota = mock.MagicMock()
        mock_base_file_node.objects.filter.return_value.order_by.return_value.first.return_value = self.base_folder_node
        folder_element = BaseFileNode(type='osf.s3folder', provider='s3', _path='/testfolder/foldername',
                _materialized_path='/testfolder/foldername', target_object_id=self.node.id, target_content_type_id=2)
        mock_base_file_node.objects.filter.return_value.all.return_value = [self.base_file_node, folder_element]
        mock_file_info.objects.get.return_value = FileInfo(file=self.base_file_node, file_size=1500)
        mock_user_quota.objects.filter.return_value.first.return_value = UserQuota(
            user=self.project_creator,
            storage_type=UserQuota.CUSTOM_STORAGE,
            max_quota=api_settings.DEFAULT_MAX_QUOTA,
            used=5500
        )
        with mock.patch('website.util.quota.BaseFileNode', mock_base_file_node):
            with mock.patch('website.util.quota.FileInfo', mock_file_info):
                with mock.patch('website.util.quota.UserQuota', mock_user_quota):
                    quota.update_used_quota(
                        self=None,
                        target=self.node,
                        user=self.user,
                        event_type=FileLog.FILE_REMOVED,
                        payload={
                            'provider': 's3',
                            'metadata': {
                                'provider': 's3',
                                'name': 'testfolder',
                                'materialized': '/testfolder',
                                'path': '/testfolder',
                                'kind': 'folder'
                            }
                        }
                    )
        user_quota = UserQuota.objects.get(
            storage_type=UserQuota.CUSTOM_STORAGE,
            user=self.project_creator
        )
        assert_equal(user_quota.used, 4000)
