# encoding: utf-8

import mock
import unittest
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests import factories
from website.addons.osfstorage.tests.utils import StorageTestCase

import datetime

from modularodm import exceptions as modm_errors

from website.models import NodeLog

from website.addons.osfstorage import utils
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
        guid = model.OsfStorageGuidFile(node=self.project, path='/baz/foo/bar')

        assert_equals(guid.path, '/baz/foo/bar')
        assert_equal(guid.path, guid.waterbutler_path)
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
        guid, created = self.node_addon.find_or_create_file_guid('/baz/foo/bar')

        assert_true(created)
        assert_equal(guid.path, '/baz/foo/bar')
        assert_equal(guid.path, guid.waterbutler_path)
        assert_equal(guid.waterbutler_path, '/baz/foo/bar')

    def test_node_addon_get_or_create_finds(self):
        guid1, created1 = self.node_addon.find_or_create_file_guid('/foo/bar')
        guid2, created2 = self.node_addon.find_or_create_file_guid('/foo/bar')

        assert_true(created1)
        assert_false(created2)
        assert_equals(guid1, guid2)


class TestOsfstorageFileNode(StorageTestCase):

    def test_root_node_exists(self):
        assert_true(self.node_settings.root_node is not None)

    def test_root_node_has_no_parent(self):
        assert_true(self.node_settings.root_node.parent is None)

    def test_node_reference(self):
        assert_equal(self.project, self.node_settings.root_node.node)

    def test_get_folder(self):
        file = model.OsfStorageFileNode(name='MOAR PYLONS', kind='file', node_settings=self.node_settings)
        folder = model.OsfStorageFileNode(name='MOAR PYLONS', kind='folder', node_settings=self.node_settings)

        _id = folder._id

        file.save()
        folder.save()

        assert_equal(folder, model.OsfStorageFileNode.get_folder(_id, self.node_settings))

    def test_get_file(self):
        file = model.OsfStorageFileNode(name='MOAR PYLONS', kind='file', node_settings=self.node_settings)
        folder = model.OsfStorageFileNode(name='MOAR PYLONS', kind='folder', node_settings=self.node_settings)

        file.save()
        folder.save()

        _id = file._id

        assert_equal(file, model.OsfStorageFileNode.get_file(_id, self.node_settings))

    def test_get_child_by_name(self):
        child = self.node_settings.root_node.append_file('Test')
        assert_equal(child, self.node_settings.root_node.find_child_by_name('Test'))

    def test_root_node_path(self):
        assert_equal(self.node_settings.root_node.name, '')

    def test_folder_path(self):
        path = '/{}/'.format(self.node_settings.root_node._id)

        assert_equal(self.node_settings.root_node.path, path)

    def test_file_path(self):
        file = model.OsfStorageFileNode(name='MOAR PYLONS', kind='file', node_settings=self.node_settings)

        assert_equal(file.name, 'MOAR PYLONS')
        assert_equal(file.path, '/{}'.format(file._id))

    def test_append_folder(self):
        child = self.node_settings.root_node.append_folder('Test')
        children = self.node_settings.root_node.children

        assert_equal(child.kind, 'folder')
        assert_equal([child], list(children))

    def test_append_file(self):
        child = self.node_settings.root_node.append_file('Test')
        children = self.node_settings.root_node.children

        assert_equal(child.kind, 'file')
        assert_equal([child], list(children))

    def test_append_to_file(self):
        child = self.node_settings.root_node.append_file('Test')
        with assert_raises(ValueError):
            child.append_file('Cant')

    def test_children(self):
        assert_equals([
            self.node_settings.root_node.append_file('Foo{}Bar'.format(x))
            for x in xrange(100)
        ], list(self.node_settings.root_node.children))

    def test_download_count_file_defaults(self):
        child = self.node_settings.root_node.append_file('Test')
        assert_equals(child.get_download_count(), 0)

    @mock.patch('framework.analytics.session')
    def test_download_count_file(self, mock_session):
        mock_session.data = {}
        child = self.node_settings.root_node.append_file('Test')

        utils.update_analytics(self.project, child._id, 0)
        utils.update_analytics(self.project, child._id, 1)
        utils.update_analytics(self.project, child._id, 2)

        assert_equals(child.get_download_count(), 3)
        assert_equals(child.get_download_count(0), 1)
        assert_equals(child.get_download_count(1), 1)
        assert_equals(child.get_download_count(2), 1)

    def test_download_count_folder(self):
        assert_is(
            None,
            self.node_settings.root_node.get_download_count()
        )

    @unittest.skip
    def test_create_version(self):
        pass

    @unittest.skip
    def test_update_version_metadata(self):
        pass

    def test_delete_folder(self):
        parent = self.node_settings.root_node.append_folder('Test')
        kids = []
        for x in range(10):
            kid = parent.append_file(str(x))
            kid.save()
            kids.append(kid)
        count = model.OsfStorageFileNode.find().count()
        tcount = model.OsfStorageTrashedFileNode.find().count()

        parent.delete()

        assert_is(model.OsfStorageFileNode.load(parent._id), None)
        assert_equals(count - 11, model.OsfStorageFileNode.find().count())
        assert_equals(tcount + 11, model.OsfStorageTrashedFileNode.find().count())

        for kid in kids:
            assert_is(
                model.OsfStorageFileNode.load(kid._id),
                None
            )

    def test_delete_file(self):
        child = self.node_settings.root_node.append_file('Test')
        child.delete()

        # assert_true(child.is_deleted)
        assert_is(model.OsfStorageFileNode.load(child._id), None)
        trashed = model.OsfStorageTrashedFileNode.load(child._id)
        child_storage = child.to_storage()
        del child_storage['is_deleted']
        assert_equal(trashed.to_storage(), child_storage)

    def test_materialized_path(self):
        child = self.node_settings.root_node.append_file('Test')
        assert_equals('/Test', child.materialized_path())

    def test_materialized_path_folder(self):
        child = self.node_settings.root_node.append_folder('Test')
        assert_equals('/Test/', child.materialized_path())

    def test_materialized_path_nested(self):
        child = self.node_settings.root_node.append_folder('Cloud').append_file('Carp')
        assert_equals('/Cloud/Carp', child.materialized_path())

    def test_copy(self):
        to_copy = self.node_settings.root_node.append_file('Carp')
        copy_to = self.node_settings.root_node.append_folder('Cloud')

        copied = to_copy.copy_under(copy_to)

        assert_not_equal(copied, to_copy)
        assert_equal(copied.parent, copy_to)
        assert_equal(to_copy.parent, self.node_settings.root_node)

    def test_copy_rename(self):
        to_copy = self.node_settings.root_node.append_file('Carp')
        copy_to = self.node_settings.root_node.append_folder('Cloud')

        copied = to_copy.copy_under(copy_to, name='But')

        assert_equal(copied.name, 'But')
        assert_not_equal(copied, to_copy)
        assert_equal(to_copy.name, 'Carp')
        assert_equal(copied.parent, copy_to)
        assert_equal(to_copy.parent, self.node_settings.root_node)

    def test_move(self):
        to_move = self.node_settings.root_node.append_file('Carp')
        move_to = self.node_settings.root_node.append_folder('Cloud')

        moved = to_move.move_under(move_to)

        assert_equal(to_move, moved)
        assert_equal(moved.parent, move_to)

    def test_move_and_rename(self):
        to_move = self.node_settings.root_node.append_file('Carp')
        move_to = self.node_settings.root_node.append_folder('Cloud')

        moved = to_move.move_under(move_to, name='Tuna')

        assert_equal(to_move, moved)
        assert_equal(to_move.name, 'Tuna')
        assert_equal(moved.parent, move_to)

    @unittest.skip
    def test_move_folder(self):
        pass

    @unittest.skip
    def test_move_folder_and_rename(self):
        pass

    @unittest.skip
    def test_rename_folder(self):
        pass

    @unittest.skip
    def test_rename_file(self):
        pass

    @unittest.skip
    def test_move_across_nodes(self):
        pass

    @unittest.skip
    def test_move_folder_across_nodes(self):
        pass

    @unittest.skip
    def test_copy_across_nodes(self):
        pass

    @unittest.skip
    def test_copy_folder_across_nodes(self):
        pass

class TestNodeSettingsModel(StorageTestCase):

    def test_fields(self):
        assert_true(self.node_settings._id)
        assert_is(self.node_settings.has_auth, True)
        assert_is(self.node_settings.complete, True)

    def test_after_fork_copies_versions(self):
        num_versions = 5
        path = 'jazz/dreamers-ball.mp3'

        record = self.node_settings.root_node.append_file(path)

        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.versions.append(version)
        record.save()

        fork = self.project.fork_node(self.auth_obj)
        fork_node_settings = fork.get_addon('osfstorage')
        fork_node_settings.reload()

        cloned_record = fork_node_settings.root_node.find_child_by_name(path)
        assert_equal(cloned_record.versions, record.versions)
        assert_true(fork_node_settings.root_node)

    '''
    OSFStorage files are now copied by Archiver
    @mock.patch('website.archiver.tasks.archive.si')
    def test_after_register_copies_versions(self, mock_archive):
        num_versions = 5
        path = 'jazz/dreamers-ball.mp3'

        record = self.node_settings.root_node.append_file(path)

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
        assert_true(registration.has_addon('osfstorage'))
        registration_node_settings = registration.get_addon('osfstorage')
        registration_node_settings.reload()
        cloned_record = registration_node_settings.root_node.find_child_by_name(path)
        assert_equal(cloned_record.versions, record.versions)
        assert_equal(cloned_record.versions, record.versions)
        assert_true(registration_node_settings.root_node)
    '''


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
        version.update_metadata({'archive': 'glacier', 'size': 123, 'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'})
        version.reload()
        assert_in('archive', version.metadata)
        assert_equal(version.metadata['archive'], 'glacier')

