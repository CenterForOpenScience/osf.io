# encoding: utf-8

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests import factories
from website.addons.osfstorage.tests.utils import StorageTestCase

import datetime

from modularodm import exceptions as modm_errors

from framework.auth import Auth

from website.models import NodeLog

from website.addons.osfstorage import model
from website.addons.osfstorage import errors
from website.addons.osfstorage import settings


class TestFileGuid(OsfTestCase):
    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.user = factories.AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.node_addon = self.project.get_addon('osfstorage')

    def test_provider(self):
        assert_equal('osfstorage', model.OsfStorageGuidFile().provider)

    def test_correct_path(self):
        guid = model.OsfStorageGuidFile(node=self.project, path='baz/foo/bar')

        assert_equals(guid.path, 'baz/foo/bar')
        assert_equals(guid.waterbutler_path, '/baz/foo/bar')

    @mock.patch('website.addons.base.requests.get')
    def test_unique_identifier(self, mock_get):
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'name': 'Morty',
                'extra': {
                    'version': 'Terran it up'
                }
            }
        }

        guid = model.OsfStorageGuidFile(node=self.project, path='/foo/bar')

        guid.enrich()
        assert_equals('Terran it up', guid.unique_identifier)

    def test_node_addon_get_or_create(self):
        guid, created = self.node_addon.find_or_create_file_guid('baz/foo/bar')

        assert_true(created)
        assert_equal(guid.path, 'baz/foo/bar')
        assert_equal(guid.waterbutler_path, '/baz/foo/bar')

    def test_node_addon_get_or_create_finds(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')
        guid2, created2 = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)


class TestNodeSettingsModel(StorageTestCase):

    def test_fields(self):
        assert_true(self.node_settings._id)
        assert_is(self.node_settings.file_tree, None)

    def test_after_fork_copies_versions(self):
        path = 'jazz/dreamers-ball.mp3'
        num_versions = 5
        record, _ = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.versions.append(version)
        record.save()
        fork = self.project.fork_node(self.auth_obj)
        fork_node_settings = fork.get_addon('osfstorage')
        fork_node_settings.reload()
        cloned_record = model.OsfStorageFileRecord.find_by_path(path, fork_node_settings)
        assert_equal(cloned_record.versions, record.versions)
        assert_true(fork_node_settings.file_tree)

    def test_after_register_copies_versions(self):
        path = 'jazz/dreamers-ball.mp3'
        num_versions = 5
        record, _ = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.versions.append(version)
        record.save()
        registration = self.project.register_node(
            None,
            self.auth_obj,
            '',
            {},
        )
        registration_node_settings = registration.get_addon('osfstorage')
        registration_node_settings.reload()
        cloned_record = model.OsfStorageFileRecord.find_by_path(path, registration_node_settings)
        assert_equal(cloned_record.versions, record.versions)
        assert_true(registration_node_settings.file_tree)


class TestOsfStorageFileTree(OsfTestCase):

    def setUp(self):
        super(TestOsfStorageFileTree, self).setUp()
        self.path = 'news/of/the/world'
        self.node_settings = model.OsfStorageNodeSettings()
        self.node_settings.save()
        self.tree = model.OsfStorageFileTree(
            path=self.path,
            node_settings=self.node_settings,
        )
        self.tree.save()

    def test_fields(self):
        assert_true(self.tree._id)
        assert_equal(self.tree.children, [])

    def test_name(self):
        assert_equal(self.tree.name, 'world')

    def test_find_by_path_found(self):
        result = model.OsfStorageFileTree.find_by_path(self.path, self.node_settings)
        assert_equal(result, self.tree)

    def test_find_by_path_not_found(self):
        result = model.OsfStorageFileTree.find_by_path('missing', self.node_settings)
        assert_is(result, None)

    def test_get_or_create_found(self):
        result, _ = model.OsfStorageFileTree.get_or_create(self.path, self.node_settings)
        assert_equal(result, self.tree)

    def test_get_or_create_not_found_top_level(self):
        assert_is(self.node_settings.file_tree, None)
        result, _ = model.OsfStorageFileTree.get_or_create('', self.node_settings)
        assert_equal(self.node_settings.file_tree, result)

    def test_get_or_create_not_found_nested(self):
        assert_is(self.node_settings.file_tree, None)
        path = 'night/at/the/opera'
        result, _ = model.OsfStorageFileTree.get_or_create(path, self.node_settings)
        assert_true(model.OsfStorageFileTree.find_by_path('', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night/at', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night/at/the', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night/at/the/opera', self.node_settings))
        assert_equal(
            self.node_settings.file_tree,
            model.OsfStorageFileTree.find_by_path('', self.node_settings),
        )

    def test_get_or_create_idempotent(self):
        path = 'night/at/the/opera'
        result, _ = model.OsfStorageFileTree.get_or_create(path, self.node_settings)
        num_trees = model.OsfStorageFileTree.find().count()
        num_records = model.OsfStorageFileRecord.find().count()
        result = model.OsfStorageFileTree.get_or_create(path, self.node_settings)
        assert_equal(num_trees, model.OsfStorageFileTree.find().count())
        assert_equal(num_records, model.OsfStorageFileRecord.find().count())


class TestOsfStorageFileRecord(StorageTestCase):

    def setUp(self):
        super(TestOsfStorageFileRecord, self).setUp()
        self.path = 'red/special.mp3'
        self.record, _ = model.OsfStorageFileRecord.get_or_create(
            path=self.path,
            node_settings=self.node_settings,
        )
        self.record.save()

    def test_fields(self):
        assert_true(self.record._id)
        assert_false(self.record.is_deleted)
        assert_equal(self.record.versions, [])

    def test_name(self):
        assert_equal(self.record.name, 'special.mp3')

    def test_extension(self):
        assert_equal(self.record.extension, '.mp3')

    def test_find_by_path_found(self):
        result = model.OsfStorageFileRecord.find_by_path(self.path, self.node_settings)
        assert_equal(result, self.record)

    def test_find_by_path_not_found(self):
        result = model.OsfStorageFileRecord.find_by_path('missing', self.node_settings)
        assert_is(result, None)

    def test_get_or_create_found(self):
        result, _ = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        assert_equal(result, self.record)

    def test_get_or_create_not_found_top_level(self):
        nchildren = len(self.node_settings.file_tree.children)
        result, _ = model.OsfStorageFileRecord.get_or_create(
            'stonecold.mp3',
            self.node_settings,
        )
        assert_is_not(self.node_settings.file_tree, None)
        assert_equal(len(self.node_settings.file_tree.children), nchildren + 1)
        assert_equal(self.node_settings.file_tree.children[-1], result)

    def test_get_or_create_not_found_nested(self):
        path = 'night/at/the/opera/39.mp3'
        result = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        assert_true(model.OsfStorageFileRecord.find_by_path(path, self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night/at', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night/at/the', self.node_settings))
        assert_true(model.OsfStorageFileTree.find_by_path('night/at/the/opera', self.node_settings))
        assert_true(model.OsfStorageFileRecord.find_by_path('night/at/the/opera/39.mp3', self.node_settings))
        assert_equal(
            self.node_settings.file_tree,
            model.OsfStorageFileTree.find_by_path('', self.node_settings),
        )

    def test_get_or_create_idempotent(self):
        path = 'night/at/the/opera/39.mp3'
        result = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        num_trees = model.OsfStorageFileTree.find().count()
        num_records = model.OsfStorageFileRecord.find().count()
        result = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        assert_equal(num_trees, model.OsfStorageFileTree.find().count())
        assert_equal(num_records, model.OsfStorageFileRecord.find().count())

    def test_get_version_defaults_found(self):
        versions = [factories.FileVersionFactory() for _ in range(3)]
        self.record.versions = versions
        assert_equal(self.record.get_version(), self.record.versions[-1])

    def test_get_version_defaults_not_found(self):
        assert_equal(self.record.get_version(), None)

    def test_get_version_at_index(self):
        versions = [factories.FileVersionFactory() for _ in range(3)]
        self.record.versions = versions
        assert_equal(self.record.get_version(1), self.record.versions[1])

    def test_get_version_required_not_found(self):
        with assert_raises(errors.VersionNotFoundError):
            self.record.get_version(required=True)

    def test_get_versions(self):
        self.record.versions = [
            factories.FileVersionFactory()
            for _ in range(15)
        ]
        self.record.save()
        indices, versions, more = self.record.get_versions(0, size=10)
        assert_equal(indices, range(15, 5, -1))
        assert_equal(
            versions,
            list(self.record.versions[14:4:-1]),
        )
        assert_true(more)
        indices, versions, more = self.record.get_versions(1, size=10)
        assert_equal(indices, range(5, 0, -1))
        assert_equal(
            versions,
            list(self.record.versions[4::-1]),
        )
        assert_false(more)

    def test_delete_record(self):
        nlogs = len(self.project.logs)
        self.record.delete(auth=self.auth_obj)
        self.project.reload()
        assert_true(self.record.is_deleted)
        assert_equal(len(self.project.logs), nlogs + 1)
        logged = self.project.logs[-1]
        assert_equal(
            logged.action,
            'osf_storage_{0}'.format(NodeLog.FILE_REMOVED),
        )
        assert_not_in('version', logged.params)

    def test_delete_deleted_record_raises_error(self):
        nlogs = len(self.project.logs)
        self.record.is_deleted = True
        self.record.save()
        with assert_raises(errors.DeleteError):
            self.record.delete(auth=self.auth_obj)
        self.project.reload()
        assert_true(self.record.is_deleted)
        assert_equal(len(self.project.logs), nlogs)

    def test_undelete_record(self):
        nlogs = len(self.project.logs)
        self.record.is_deleted = True
        self.record.save()
        self.record.undelete(auth=self.auth_obj)
        self.project.reload()
        assert_false(self.record.is_deleted)
        assert_equal(len(self.project.logs), nlogs + 1)
        assert_equal(
            self.project.logs[-1].action,
            'osf_storage_{0}'.format(NodeLog.FILE_ADDED),
        )

    def test_undelete_undeleted_record_raises_error(self):
        nlogs = len(self.project.logs)
        with assert_raises(errors.UndeleteError):
            self.record.undelete(auth=self.auth_obj)
        assert_false(self.record.is_deleted)
        self.project.reload()
        assert_false(self.record.is_deleted)
        assert_equal(len(self.project.logs), nlogs)

    def test_update_metadata_found(self):
        self.record.versions = [
            factories.FileVersionFactory(),
            factories.FileVersionFactory(),
        ]
        self.record.versions[0].location['object'] = 'foo'
        self.record.versions[1].location['object'] = 'bar'
        self.record.versions[0].save()
        self.record.versions[1].save()
        self.record.save()
        self.record.update_version_metadata(self.record.versions[0].location, {'archive': 'glacier'})
        assert_in('archive', self.record.versions[0].metadata)
        assert_equal(self.record.versions[0].metadata['archive'], 'glacier')
        assert_not_in('archive', self.record.versions[1].metadata)

    def test_update_metadata_not_found(self):
        self.record.versions = [
            factories.FileVersionFactory(signature='31a64'),
            factories.FileVersionFactory(signature='7aa12'),
        ]
        self.record.save()
        with assert_raises(errors.VersionNotFoundError):
            self.record.update_version_metadata('1143b3', {'archive': 'glacier'})
        assert_not_in('archive', self.record.versions[0].metadata)
        assert_not_in('archive', self.record.versions[1].metadata)


class TestOsfStorageFileVersion(OsfTestCase):

    def setUp(self):
        super(TestOsfStorageFileVersion, self).setUp()
        self.user = factories.AuthUserFactory()
        self.mock_date = datetime.datetime(1991, 10, 31)

    def test_fields(self):
        version = factories.FileVersionFactory(
            size=1024,
            content_type='application/json',
            date_modified=datetime.datetime.now(),
        )
        retrieved = model.OsfStorageFileVersion.load(version._id)
        assert_true(retrieved.creator)
        assert_true(retrieved.location)
        assert_true(retrieved.size)
        assert_true(retrieved.content_type)
        assert_true(retrieved.date_modified)

    def test_is_duplicate_true(self):
        version1 = factories.FileVersionFactory()
        version2 = factories.FileVersionFactory()
        assert_true(version1.is_duplicate(version2))
        assert_true(version2.is_duplicate(version1))

    def test_is_duplicate_false(self):
        version1 = factories.FileVersionFactory(
            location={
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': 'd077f2',
            },
        )
        version2 = factories.FileVersionFactory(
            location={
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': '06d80e',
            },
        )
        assert_false(version1.is_duplicate(version2))
        assert_false(version2.is_duplicate(version1))

    def test_validate_location(self):
        version = factories.FileVersionFactory.build(location={})
        with assert_raises(modm_errors.ValidationValueError):
            version.save()
        version.location = {
            'service': 'cloud',
            settings.WATERBUTLER_RESOURCE: 'osf',
            'object': 'object',
        }
        version.save()

    def test_update_metadata(self):
        version = factories.FileVersionFactory()
        version.update_metadata({'archive': 'glacier'})
        assert_in('archive', version.metadata)
        assert_equal(version.metadata['archive'], 'glacier')


class TestStorageObject(OsfTestCase):

    def setUp(self):
        super(TestStorageObject, self).setUp()
        self.project = ProjectFactory()
        self.path = 'kind/of/magic.mp3'

    def test_fields(self):
        file_obj = model.OsfStorageGuidFile(node=self.project, path=self.path)
        file_obj.save()
        assert_true(file_obj._id)
        assert_equal(file_obj.node, self.project)
        assert_equal(file_obj.path, self.path)

    def test_field_validation(self):
        file_obj = model.OsfStorageGuidFile(node=self.project)
        with assert_raises(modm_errors.ValidationError):
            file_obj.save()

    def test_get_download_path(self):
        file_obj = model.OsfStorageGuidFile(node=self.project, path=self.path)
        file_obj.save()
        version = 3
        assert_equal(
            file_obj.get_download_path(version),
            '/{0}/?action=download&version={1}&mode=render'.format(
                file_obj._id, version,
            ),
        )

    def test_get_or_create_exists(self):
        existing = model.OsfStorageGuidFile(node=self.project, path=self.path)
        existing.save()
        n_objs = model.OsfStorageGuidFile.find().count()
        result, _ = model.OsfStorageGuidFile.get_or_create(self.project, self.path)
        assert_equal(result, existing)
        assert_equal(n_objs, model.OsfStorageGuidFile.find().count())

    def test_get_or_create_does_not_exist(self):
        n_objs = model.OsfStorageGuidFile.find().count()
        result, _ = model.OsfStorageGuidFile.get_or_create(self.project, self.path)
        assert_equal(result.node, self.project)
        assert_equal(result.path, self.path)
        assert_equal(n_objs + 1, model.OsfStorageGuidFile.find().count())
