# encoding: utf-8

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests import factories
from website.addons.osfstorage.tests.utils import StorageTestCase

import os
import datetime

from dateutil.relativedelta import relativedelta
from modularodm import exceptions as modm_errors

from framework.auth import Auth

from website.models import NodeLog

from website.addons.osfstorage import logs
from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import errors
from website.addons.osfstorage import settings


class TestNodeSettingsModel(StorageTestCase):

    def test_fields(self):
        assert_true(self.node_settings._id)
        assert_is(self.node_settings.file_tree, None)

    def test_after_fork_copies_stable_versions(self):
        path = 'jazz/dreamers-ball.mp3'
        num_versions = 5
        record = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.versions.append(version)
        record.versions[-1].status = model.status_map['UPLOADING']
        record.versions[-1].save()
        record.versions[-2].status = model.status_map['CACHED']
        record.versions[-2].save()
        record.save()
        fork = self.project.fork_node(self.auth_obj)
        fork_node_settings = fork.get_addon('osfstorage')
        fork_node_settings.reload()
        cloned_record = model.OsfStorageFileRecord.find_by_path(path, fork_node_settings)
        assert_equal(cloned_record.versions, record.versions[:num_versions - 2])
        assert_true(fork_node_settings.file_tree)

    def test_after_register_copies_stable_versions(self):
        path = 'jazz/dreamers-ball.mp3'
        num_versions = 5
        record = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.versions.append(version)
        record.versions[-1].status = model.status_map['UPLOADING']
        record.versions[-1].save()
        record.versions[-2].status = model.status_map['CACHED']
        record.versions[-2].save()
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
        assert_equal(cloned_record.versions, record.versions[:num_versions - 2])
        assert_true(registration_node_settings.file_tree)

    def test_after_fork_copies_stable_records(self):
        path = 'jazz/dreamers-ball.mp3'
        record = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        version_pending = factories.FileVersionFactory(status=model.status_map['UPLOADING'])
        record.versions.append(version_pending)
        record.save()
        fork = self.project.fork_node(self.auth_obj)
        fork_node_settings = fork.get_addon('osfstorage')
        cloned_record = model.OsfStorageFileRecord.find_by_path(path, fork_node_settings)
        assert_is(cloned_record, None)

    def test_after_register_copies_stable_records(self):
        path = 'jazz/dreamers-ball.mp3'
        record = model.OsfStorageFileRecord.get_or_create(path, self.node_settings)
        version_pending = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
        )
        version_pending.save()
        record.versions.append(version_pending)
        record.save()
        registration = self.project.register_node(
            None,
            self.auth_obj,
            '',
            {},
        )
        registration_node_settings = registration.get_addon('osfstorage')
        cloned_record = model.OsfStorageFileRecord.find_by_path(path, registration_node_settings)
        assert_is(cloned_record, None)


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

    def test_touch(self):
        assert_is(self.tree.touch(), True)

    def test_parent_root(self):
        tree = model.OsfStorageFileTree.get_or_create('', self.node_settings)
        assert_is(tree.parent, None)

    def test_parent_branch(self):
        tree = model.OsfStorageFileTree.get_or_create('branch', self.node_settings)
        expected_parent = model.OsfStorageFileTree.get_or_create('', self.node_settings)
        assert_equal(tree.parent, expected_parent)

    def test_find_by_path_found(self):
        result = model.OsfStorageFileTree.find_by_path(self.path, self.node_settings)
        assert_equal(result, self.tree)

    def test_find_by_path_not_found(self):
        result = model.OsfStorageFileTree.find_by_path('missing', self.node_settings)
        assert_is(result, None)

    def test_get_or_create_found(self):
        result = model.OsfStorageFileTree.get_or_create(self.path, self.node_settings)
        assert_equal(result, self.tree)

    def test_get_or_create_not_found_top_level(self):
        assert_is(self.node_settings.file_tree, None)
        result = model.OsfStorageFileTree.get_or_create('', self.node_settings)
        assert_equal(self.node_settings.file_tree, result)

    def test_get_or_create_not_found_nested(self):
        assert_is(self.node_settings.file_tree, None)
        path = 'night/at/the/opera'
        result = model.OsfStorageFileTree.get_or_create(path, self.node_settings)
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
        result = model.OsfStorageFileTree.get_or_create(path, self.node_settings)
        num_trees = model.OsfStorageFileTree.find().count()
        num_records = model.OsfStorageFileRecord.find().count()
        result = model.OsfStorageFileTree.get_or_create(path, self.node_settings)
        assert_equal(num_trees, model.OsfStorageFileTree.find().count())
        assert_equal(num_records, model.OsfStorageFileRecord.find().count())


class TestOsfStorageFileRecord(StorageTestCase):

    def setUp(self):
        super(TestOsfStorageFileRecord, self).setUp()
        self.path = 'red/special.mp3'
        self.record = model.OsfStorageFileRecord.get_or_create(
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
        result = model.OsfStorageFileRecord.get_or_create(self.path, self.node_settings)
        assert_equal(result, self.record)

    def test_get_or_create_not_found_top_level(self):
        nchildren = len(self.node_settings.file_tree.children)
        result = model.OsfStorageFileRecord.get_or_create(
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

    def test_create_pending(self):
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            factories.generic_location,
            {
                'size': 7,
                'content_type': 'text/plain',
                'date_modified': '2014-11-06 22:38',
            },
        )
        self.record.create_pending_version(self.user, '78c9a53')

    def test_create_pending_record_deleted(self):
        self.record.delete(self.auth_obj, log=False)
        assert_true(self.record.is_deleted)
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            factories.generic_location,
            {
                'size': 7,
                'content_type': 'text/plain',
                'date_modified': datetime.datetime.utcnow().isoformat(),
            },
        )
        assert_false(self.record.is_deleted)
        self.record.create_pending_version(self.user, '78c9a53')

    def test_create_pending_previous_cancelled(self):
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.cancel_pending_version('c22b59f')

    def test_create_pending_path_locked(self):
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
            date_created=datetime.datetime.utcnow(),
        )
        version.save()
        self.record.versions.append(version)
        with assert_raises(errors.PathLockedError):
            self.record.create_pending_version(self.user, 'c22b5f9')

    def test_create_pending_bad_signature(self):
        version = factories.FileVersionFactory(
            signature='c22b5f9',
        )
        self.record.versions.append(version)
        with assert_raises(errors.SignatureConsumedError):
            self.record.create_pending_version(self.user, 'c22b5f9')

    def test_set_pending_cached(self):
        version = factories.FileVersionFactory(status=model.status_map['UPLOADING'])
        self.record.versions.append(version)
        self.record.save()
        self.record.set_pending_version_cached(version.signature)
        assert_equal(version.status, model.status_map['CACHED'])

    def test_set_pending_cached_no_versions(self):
        with assert_raises(errors.VersionNotFoundError):
            self.record.set_pending_version_cached('06d80e')

    def test_cancel_uploading(self):
        version = factories.FileVersionFactory(status=model.status_map['UPLOADING'])
        version.cancel(version.signature)

    def test_cancel_not_uploading_raises_error(self):
        version = factories.FileVersionFactory(status=model.status_map['CACHED'])
        with assert_raises(errors.VersionStatusError):
            version.cancel(version.signature)
        version = factories.FileVersionFactory(status=model.status_map['COMPLETE'])
        with assert_raises(errors.VersionStatusError):
            version.cancel(version.signature)

    def test_cancel_bad_signature(self):
        version = factories.FileVersionFactory(status=model.status_map['UPLOADING'])
        with assert_raises(errors.SignatureMismatchError):
            version.cancel(version.signature[::-1])

    def test_resolve_pending_logs_file_creation(self):
        nlogs = len(self.project.logs)
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            factories.generic_location,
            {
                'size': 7,
                'content_type': 'text/plain',
                'date_modified': '2014-11-06 22:38',
            },
        )
        assert_equal(len(self.project.logs), nlogs + 1)
        logged = self.project.logs[-1]
        assert_equal(
            logged.action,
            'osf_storage_{0}'.format(NodeLog.FILE_ADDED),
        )
        assert_equal(logged.user, self.user)
        assert_equal(
            logged.params['urls'],
            logs.build_log_urls(self.project, self.path),
        )
        assert_equal(logged.params['version'], len(self.record.versions))

    def test_resolve_pending_logs_file_update(self):
        nlogs = len(self.project.logs)
        version = factories.FileVersionFactory()
        self.record.versions.append(version)
        self.record.save()
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            {
                'service': 'cloud',
                'container': 'container',
                'object': '7035161',
            },
            {
                'size': 7,
                'content_type': 'text/plain',
                'date_modified': '2014-11-06 22:38',
            },
        )
        self.project.reload()
        assert_equal(len(self.project.logs), nlogs + 1)
        logged = self.project.logs[-1]
        assert_equal(logged.user, self.user)
        assert_equal(
            logged.action,
            'osf_storage_{0}'.format(NodeLog.FILE_UPDATED),
        )
        assert_equal(
            logged.params['urls'],
            logs.build_log_urls(self.project, self.path),
        )
        assert_equal(logged.params['version'], len(self.record.versions))

    def test_resolve_pending_duplicate_delete_version_without_log(self):
        version = factories.FileVersionFactory()
        self.record.versions.append(version)
        self.record.save()
        nversions = model.OsfStorageFileVersion.find().count()
        nversions_record = len(self.record.versions)
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            factories.generic_location,
            {
                'size': 7,
                'content_type': 'text/plain',
                'date_modified': '2014-11-06 22:38',
            },
        )
        self.project.reload()
        logged = self.project.logs[-1]
        assert_equal(
            logged.action,
            'osf_storage_{0}'.format(NodeLog.FILE_UPDATED),
        )
        assert_equal(logged.params['version'], len(self.record.versions))

    def test_remove_version_one_version(self):
        parent = self.record.parent
        assert_equal(len(parent.children), 1)
        version = factories.FileVersionFactory()
        self.record.versions = [version]
        self.record.save()
        retained_self = self.record.remove_version(version)
        assert_false(retained_self)
        model.OsfStorageFileRecord._clear_caches()
        model.OsfStorageFileVersion._clear_caches()
        assert_is(model.OsfStorageFileRecord.load(self.record._id), None)
        assert_is(model.OsfStorageFileVersion.load(version._id), None)
        assert_equal(len(parent.children), 0)

    def test_remove_version_two_versions(self):
        parent = self.record.parent
        assert_equal(len(parent.children), 1)
        versions = [factories.FileVersionFactory() for _ in range(3)]
        self.record.versions = versions
        self.record.save()
        retained_self = self.record.remove_version(versions[-1])
        assert_is(retained_self, True)
        model.OsfStorageFileRecord._clear_caches()
        model.OsfStorageFileVersion._clear_caches()
        assert_true(model.OsfStorageFileRecord.load(self.record._id))
        assert_is(model.OsfStorageFileVersion.load(versions[-1]._id), None)
        assert_equal(len(parent.children), 1)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_touch_pending_one_version_not_expired(self, mock_time):
        mock_time.return_value = 10
        version = self.record.create_pending_version(self.user, 'c22b59f')
        valid = self.record.touch()
        assert_is(valid, True)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_touch_pending_one_version_expired(self, mock_time):
        mock_time.return_value = 0
        version = self.record.create_pending_version(self.user, 'c22b59f')
        mock_time.return_value = settings.PING_TIMEOUT + 1
        valid = self.record.touch()
        assert_is(valid, False)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_touch_pending_many_versions_not_expired(self, mock_time):
        mock_time.return_value = 10
        self.record.versions = [factories.FileVersionFactory() for _ in range(5)]
        self.record.save()
        version = self.record.create_pending_version(self.user, 'c22b59f')
        valid = self.record.touch()
        assert_is(valid, True)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_touch_pending_many_versions_expired(self, mock_time):
        mock_time.return_value = 0
        self.record.versions = [factories.FileVersionFactory() for _ in range(5)]
        self.record.save()
        version = self.record.create_pending_version(self.user, 'c22b59f')
        mock_time.return_value = settings.PING_TIMEOUT + 1
        valid = self.record.touch()
        assert_is(valid, True)

    def test_touch_not_pending(self):
        self.record.versions.append(factories.FileVersionFactory())
        valid = self.record.touch()
        assert_is(valid, True)

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
            'osf_storage_{0}'.format(NodeLog.FILE_RESTORED),
        )

    def test_undelete_undeleted_record_raises_error(self):
        nlogs = len(self.project.logs)
        with assert_raises(errors.UndeleteError):
            self.record.undelete(auth=self.auth_obj)
        assert_false(self.record.is_deleted)
        self.project.reload()
        assert_false(self.record.is_deleted)
        assert_equal(len(self.project.logs), nlogs)


class TestOsfStorageFileVersion(OsfTestCase):

    def setUp(self):
        super(TestOsfStorageFileVersion, self).setUp()
        self.user = factories.AuthUserFactory()
        self.mock_date = datetime.datetime(1991, 10, 31)

    def test_fields(self):
        version = factories.FileVersionFactory(
            signature='c22b5f9',
            size=1024,
            content_type='application/json',
            date_modified=datetime.datetime.now(),
        )
        retrieved = model.OsfStorageFileVersion.load(version._id)
        assert_true(retrieved.status)
        assert_true(retrieved.creator)
        assert_true(retrieved.location)
        assert_true(retrieved.signature)
        assert_true(retrieved.size)
        assert_true(retrieved.content_type)
        assert_true(retrieved.date_modified)

    def test_is_duplicate_no_location(self):
        version1 = factories.FileVersionFactory(
            status=model.status_map['UPLOADING'],
            location={},
        )
        version2 = factories.FileVersionFactory(
            status=model.status_map['UPLOADING'],
            location={},
        )
        assert_false(version1.is_duplicate(version2))
        assert_false(version2.is_duplicate(version1))

    def test_is_duplicate_has_location_is_duplicate(self):
        version1 = factories.FileVersionFactory()
        version2 = factories.FileVersionFactory()
        assert_true(version1.is_duplicate(version2))
        assert_true(version2.is_duplicate(version1))

    def test_is_duplicate_has_location_is_not_duplicate(self):
        version1 = factories.FileVersionFactory(
            location={
                'service': 'cloud',
                'container': 'osf',
                'object': 'd077f2',
            },
        )
        version2 = factories.FileVersionFactory(
            location={
                'service': 'cloud',
                'container': 'osf',
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
            'container': 'container',
            'object': 'object',
        }
        version.save()

    def test_validate_dates(self):
        version = factories.FileVersionFactory.build(date_resolved=None)
        with assert_raises(modm_errors.ValidationValueError):
            version.save()
        version.date_resolved = version.date_created - relativedelta(seconds=1)
        with assert_raises(modm_errors.ValidationValueError):
            version.save()
        version.date_resolved = version.date_created + relativedelta(seconds=1)
        version.save()

    @mock.patch('website.addons.osfstorage.model.datetime.datetime')
    def test_resolve_uploading(self, mock_datetime):
        mock_datetime.now.return_value = self.mock_date
        mock_datetime.utcnow.return_value = self.mock_date
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
            date_created=datetime.datetime.utcnow(),
            signature='c22b5f9',
        )
        metadata = {
            'size': 1024,
            'content_type': 'text/plain',
            'date_modified': self.mock_date.isoformat(),
            'md5': '3f92d3',
        }
        version.resolve('c22b5f9', factories.generic_location, metadata)
        assert_equal(version.date_resolved, self.mock_date)
        assert_equal(version.status, model.status_map['COMPLETE'])
        assert_equal(version.size, 1024)
        assert_equal(version.content_type, 'text/plain')
        assert_equal(version.date_modified, self.mock_date)
        assert_equal(version.metadata, metadata)

    @mock.patch('website.addons.osfstorage.model.datetime.datetime')
    def test_resolve_cached(self, mock_datetime):
        mock_datetime.now.return_value = self.mock_date
        mock_datetime.utcnow.return_value = self.mock_date
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['CACHED'],
            date_created=datetime.datetime.utcnow(),
            signature='c22b5f9',
        )
        metadata = {
            'size': 1024,
            'content_type': 'text/plain',
            'date_modified': self.mock_date.isoformat(),
            'md5': '3f92d3',
        }
        version.resolve('c22b5f9', factories.generic_location, metadata)
        assert_equal(version.date_resolved, self.mock_date)
        assert_equal(version.status, model.status_map['COMPLETE'])
        assert_equal(version.size, 1024)
        assert_equal(version.content_type, 'text/plain')
        assert_equal(version.date_modified, self.mock_date)
        assert_equal(version.metadata, metadata)

    @mock.patch('website.addons.osfstorage.model.datetime.datetime')
    def test_resolve_complete_raises_error(self, mock_datetime):
        mock_datetime.now.return_value = self.mock_date
        mock_datetime.utcnow.return_value = self.mock_date
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['COMPLETE'],
            date_created=datetime.datetime.utcnow(),
            signature='c22b5f9',
        )
        metadata = {
            'size': 1024,
            'content_type': 'text/plain',
            'date_modified': self.mock_date.isoformat(),
            'md5': '3f92d3',
        }
        with assert_raises(errors.VersionStatusError):
            version.resolve('c22b5f9', factories.generic_location, metadata)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_ping_uploading(self, mock_time):
        mock_time.return_value = 10
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
            signature='c22b5f9',
        )
        assert_equal(version.last_ping, mock_time.return_value)
        mock_time.return_value = 20
        version.ping(version.signature)
        assert_equal(version.last_ping, mock_time.return_value)

    def test_ping_not_uploading_raises_error(self):
        version = factories.FileVersionFactory(status=model.status_map['CACHED'])
        with assert_raises(errors.VersionStatusError):
            version.ping(version.signature)
        version = factories.FileVersionFactory(status=model.status_map['COMPLETE'])
        with assert_raises(errors.VersionStatusError):
            version.ping(version.signature)

    def test_ping_bad_signature(self):
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
            signature='c22b5f9',
        )
        with assert_raises(errors.SignatureMismatchError):
            version.ping(version.signature[::-1])

    def test_expired_not_pending(self):
        version = factories.FileVersionFactory(status=model.status_map['CACHED'])
        assert_false(version.expired)
        version = factories.FileVersionFactory(status=model.status_map['COMPLETE'])
        assert_false(version.expired)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_expired_pending_inactive(self, mock_time):
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
            signature='c22b5f9',
            last_ping=0,
        )
        mock_time.return_value = settings.PING_TIMEOUT + 1
        assert_true(version.expired)

    @mock.patch('website.addons.osfstorage.model.time.time')
    def test_expired_pending_active(self, mock_time):
        mock_time.return_value = 0
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
            signature='c22b5f9',
            last_ping=0,
        )
        assert_false(version.expired)

    def test_finish_not_pending(self):
        version = factories.FileVersionFactory()
        with assert_raises(errors.VersionStatusError):
            version.resolve(None, {}, {})

    def test_finish_bad_signature(self):
        version = model.OsfStorageFileVersion(
            creator=self.user,
            status=model.status_map['UPLOADING'],
            date_created=datetime.datetime.utcnow(),
            signature='c22b5f9',
        )
        version.save()
        with assert_raises(errors.SignatureMismatchError):
            version.resolve(
                '78c9a53',
                factories.generic_location,
                {},
            )


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
        result = model.OsfStorageGuidFile.get_or_create(self.project, self.path)
        assert_equal(result, existing)
        assert_equal(n_objs, model.OsfStorageGuidFile.find().count())

    def test_get_or_create_does_not_exist(self):
        n_objs = model.OsfStorageGuidFile.find().count()
        result = model.OsfStorageGuidFile.get_or_create(self.project, self.path)
        assert_equal(result.node, self.project)
        assert_equal(result.path, self.path)
        assert_equal(n_objs + 1, model.OsfStorageGuidFile.find().count())
