#!/usr/bin/env python
# encoding: utf-8

import mock
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests import factories

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


class TestNodeSettingsModel(OsfTestCase):

    def setUp(self):
        super(TestNodeSettingsModel, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator
        self.node_settings = self.node.get_addon('osfstorage')

    def test_fields(self):
        assert_true(self.node_settings._id)
        assert_is(self.node_settings.file_tree, None)

    def test_after_fork_copies_stable_versions(self):
        path = 'jazz/dreamers-ball.mp3'
        num_versions = 5
        record = model.FileRecord.get_or_create(path, self.node_settings)
        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.versions.append(version)
        record.versions[-1].status = model.status['PENDING']
        record.versions[-1].save()
        record.versions[-2].status = model.status['FAILED']
        record.versions[-2].save()
        record.save()
        fork = self.node.fork_node(Auth(user=self.node.creator))
        fork_node_settings = fork.get_addon('osfstorage')
        fork_node_settings.reload()
        cloned_record = model.FileRecord.find_by_path(path, fork_node_settings)
        assert_equal(cloned_record.versions, record.versions[:num_versions - 2])
        assert_true(fork_node_settings.file_tree)

    def test_after_register_copies_stable_versions(self):
        path = 'jazz/dreamers-ball.mp3'
        num_versions = 5
        record = model.FileRecord.get_or_create(path, self.node_settings)
        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.versions.append(version)
        record.versions[-1].status = model.status['PENDING']
        record.versions[-1].save()
        record.versions[-2].status = model.status['FAILED']
        record.versions[-2].save()
        record.save()
        registration = self.node.register_node(
            None,
            Auth(user=self.node.creator),
            '',
            {},
        )
        registration_node_settings = registration.get_addon('osfstorage')
        registration_node_settings.reload()
        cloned_record = model.FileRecord.find_by_path(path, registration_node_settings)
        assert_equal(cloned_record.versions, record.versions[:num_versions - 2])
        assert_true(registration_node_settings.file_tree)

    def test_after_fork_copies_stable_records(self):
        path = 'jazz/dreamers-ball.mp3'
        record = model.FileRecord.get_or_create(path, self.node_settings)
        version_pending = model.FileVersion(
            status=model.status['PENDING'],
            date_created=datetime.datetime.utcnow(),
        )
        version_pending.save()
        version_failed = model.FileVersion(
            status=model.status['FAILED'],
            date_created=datetime.datetime.utcnow(),
        )
        version_failed.save()
        record.versions.extend([version_pending, version_failed])
        record.save()
        fork = self.node.fork_node(Auth(user=self.node.creator))
        fork_node_settings = fork.get_addon('osfstorage')
        cloned_record = model.FileRecord.find_by_path(path, fork_node_settings)
        assert_is(cloned_record, None)

    def test_after_fork_copies_stable_records(self):
        path = 'jazz/dreamers-ball.mp3'
        record = model.FileRecord.get_or_create(path, self.node_settings)
        version_pending = model.FileVersion(
            creator=self.user,
            status=model.status['PENDING'],
            date_created=datetime.datetime.utcnow(),
        )
        version_pending.save()
        version_failed = model.FileVersion(
            creator=self.user,
            status=model.status['FAILED'],
            date_created=datetime.datetime.utcnow(),
        )
        version_failed.save()
        record.versions.extend([version_pending, version_failed])
        record.save()
        registration = self.node.register_node(
            None,
            Auth(user=self.node.creator),
            '',
            {},
        )
        registration_node_settings = registration.get_addon('osfstorage')
        cloned_record = model.FileRecord.find_by_path(path, registration_node_settings)
        assert_is(cloned_record, None)


class TestFileTree(OsfTestCase):

    def setUp(self):
        super(TestFileTree, self).setUp()
        self.path = 'news/of/the/world'
        self.node_settings = model.OsfStorageNodeSettings()
        self.node_settings.save()
        self.tree = model.FileTree(
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
        result = model.FileTree.find_by_path(self.path, self.node_settings)
        assert_equal(result, self.tree)

    def test_find_by_path_not_found(self):
        result = model.FileTree.find_by_path('missing', self.node_settings)
        assert_is(result, None)

    def test_get_or_create_found(self):
        result = model.FileTree.get_or_create(self.path, self.node_settings)
        assert_equal(result, self.tree)

    def test_get_or_create_not_found_top_level(self):
        assert_is(self.node_settings.file_tree, None)
        result = model.FileTree.get_or_create('', self.node_settings)
        assert_equal(self.node_settings.file_tree, result)

    def test_get_or_create_not_found_nested(self):
        assert_is(self.node_settings.file_tree, None)
        path = 'night/at/the/opera'
        result = model.FileTree.get_or_create(path, self.node_settings)
        assert_true(model.FileTree.find_by_path('', self.node_settings))
        assert_true(model.FileTree.find_by_path('night', self.node_settings))
        assert_true(model.FileTree.find_by_path('night/at', self.node_settings))
        assert_true(model.FileTree.find_by_path('night/at/the', self.node_settings))
        assert_true(model.FileTree.find_by_path('night/at/the/opera', self.node_settings))
        assert_equal(
            self.node_settings.file_tree,
            model.FileTree.find_by_path('', self.node_settings),
        )

    def test_get_or_create_idempotent(self):
        path = 'night/at/the/opera'
        result = model.FileTree.get_or_create(path, self.node_settings)
        num_trees = model.FileTree.find().count()
        num_records = model.FileRecord.find().count()
        result = model.FileTree.get_or_create(path, self.node_settings)
        assert_equal(num_trees, model.FileTree.find().count())
        assert_equal(num_records, model.FileRecord.find().count())


class TestFileRecord(OsfTestCase):

    def setUp(self):
        super(TestFileRecord, self).setUp()
        self.path = 'red/special.mp3'
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.auth_obj = Auth(user=self.user)
        self.node_settings = self.project.get_addon('osfstorage')
        self.record = model.FileRecord(
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
        result = model.FileRecord.find_by_path(self.path, self.node_settings)
        assert_equal(result, self.record)

    def test_find_by_path_not_found(self):
        result = model.FileRecord.find_by_path('missing', self.node_settings)
        assert_is(result, None)

    def test_get_or_create_found(self):
        result = model.FileRecord.get_or_create(self.path, self.node_settings)
        assert_equal(result, self.record)

    def test_get_or_create_not_found_top_level(self):
        assert_is(self.node_settings.file_tree, None)
        result = model.FileRecord.get_or_create(
            'stonecold.mp3',
            self.node_settings,
        )
        assert_is_not(self.node_settings.file_tree, None)
        assert_equal(len(self.node_settings.file_tree.children), 1)
        assert_equal(self.node_settings.file_tree.children[0], result)

    def test_get_or_create_not_found_nested(self):
        assert_is(self.node_settings.file_tree, None)
        path = 'night/at/the/opera/39.mp3'
        result = model.FileRecord.get_or_create(path, self.node_settings)
        assert_true(model.FileRecord.find_by_path(path, self.node_settings))
        assert_true(model.FileTree.find_by_path('', self.node_settings))
        assert_true(model.FileTree.find_by_path('night', self.node_settings))
        assert_true(model.FileTree.find_by_path('night/at', self.node_settings))
        assert_true(model.FileTree.find_by_path('night/at/the', self.node_settings))
        assert_true(model.FileTree.find_by_path('night/at/the/opera', self.node_settings))
        assert_true(model.FileRecord.find_by_path('night/at/the/opera/39.mp3', self.node_settings))
        assert_equal(
            self.node_settings.file_tree,
            model.FileTree.find_by_path('', self.node_settings),
        )

    def test_get_or_create_idempotent(self):
        path = 'night/at/the/opera/39.mp3'
        result = model.FileRecord.get_or_create(path, self.node_settings)
        num_trees = model.FileTree.find().count()
        num_records = model.FileRecord.find().count()
        result = model.FileRecord.get_or_create(path, self.node_settings)
        assert_equal(num_trees, model.FileTree.find().count())
        assert_equal(num_records, model.FileRecord.find().count())

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
            {},
        )
        self.record.create_pending_version(self.user, '78c9a53')

    def test_create_pending_record_deleted(self):
        self.record.delete(self.auth_obj, log=False)
        assert_true(self.record.is_deleted)
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            factories.generic_location,
            {},
        )
        assert_false(self.record.is_deleted)
        self.record.create_pending_version(self.user, '78c9a53')

    def test_create_pending_previous_cancelled(self):
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.cancel_pending_version('c22b59f')
        self.record.create_pending_version(self.user, '78c9a53')

    def test_create_pending_path_locked(self):
        version = model.FileVersion(
            creator=self.user,
            status=model.status['PENDING'],
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

    def test_resolve_pending_logs_file_creation(self):
        nlogs = len(self.project.logs)
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            factories.generic_location,
            {'size': 1024},
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
            {'size': 1024},
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

    def test_resolve_pending_duplicate_delete_version_without_log(self):
        nlogs = len(self.project.logs)
        version = factories.FileVersionFactory()
        self.record.versions.append(version)
        self.record.save()
        nversions = model.FileVersion.find().count()
        nversions_record = len(self.record.versions)
        self.record.create_pending_version(self.user, 'c22b59f')
        self.record.resolve_pending_version(
            'c22b59f',
            factories.generic_location,
            {'size': 1024},
        )
        self.project.reload()
        self.record.reload()
        assert_equal(len(self.project.logs), nlogs)
        assert_equal(nversions, model.FileVersion.find().count())
        assert_equal(nversions_record, len(self.record.versions))

    def test_delete_record(self):
        nlogs = len(self.project.logs)
        self.record.delete(auth=self.auth_obj)
        self.project.reload()
        assert_true(self.record.is_deleted)
        assert_equal(len(self.project.logs), nlogs + 1)
        assert_equal(
            self.project.logs[-1].action,
            'osf_storage_{0}'.format(NodeLog.FILE_REMOVED),
        )

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


class TestFileVersion(OsfTestCase):

    def setUp(self):
        super(TestFileVersion, self).setUp()
        self.user = factories.AuthUserFactory()
        self.mock_date = datetime.datetime(1991, 10, 31)

    def test_fields(self):
        version = factories.FileVersionFactory(
            signature='c22b5f9',
            size=1024,
            content_type='application/json',
            date_modified=datetime.datetime.now(),
        )
        retrieved = model.FileVersion.load(version._id)
        assert_true(retrieved.creator)
        assert_true(retrieved.status)
        assert_true(retrieved.location)
        assert_true(retrieved.signature)
        assert_true(retrieved.size)
        assert_true(retrieved.content_type)
        assert_true(retrieved.date_modified)

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
    def test_resolve(self, mock_datetime):
        mock_datetime.utcnow.return_value = self.mock_date
        version = model.FileVersion(
            creator=self.user,
            status=model.status['PENDING'],
            date_created=datetime.datetime.utcnow(),
            signature='c22b5f9',
        )
        version.resolve(
            'c22b5f9',
            factories.generic_location,
            {'size': 1024},
        )
        assert_equal(version.date_resolved, self.mock_date)
        assert_equal(version.status, model.status['COMPLETE'])
        assert_equal(version.size, 1024)

    def test_cancel(self):
        version = model.FileVersion(
            creator=self.user,
            status=model.status['PENDING'],
            date_created=datetime.datetime.utcnow(),
            signature='c22b5f9',
        )
        version.cancel('c22b5f9')
        assert_equal(version.status, model.status['FAILED'])

    def test_finish_not_pending(self):
        version = factories.FileVersionFactory()
        with assert_raises(errors.VersionNotPendingError):
            version.resolve(None, {}, {})
        with assert_raises(errors.VersionNotPendingError):
            version.cancel(None)

    def test_finish_bad_signature(self):
        version = model.FileVersion(
            creator=self.user,
            status=model.status['PENDING'],
            date_created=datetime.datetime.utcnow(),
            signature='c22b5f9',
        )
        version.save()
        with assert_raises(errors.PendingSignatureMismatchError):
            version.resolve(
                '78c9a53',
                factories.generic_location,
                {},
            )
        with assert_raises(errors.PendingSignatureMismatchError):
            version.cancel('78c9a53')


class TestStorageObject(OsfTestCase):

    def setUp(self):
        super(TestStorageObject, self).setUp()
        self.project = ProjectFactory()
        self.path = 'kind/of/magic.mp3'

    def test_fields(self):
        file_obj = model.StorageFile(node=self.project, path=self.path)
        file_obj.save()
        assert_true(file_obj._id)
        assert_equal(file_obj.node, self.project)
        assert_equal(file_obj.path, self.path)

    def test_field_validation(self):
        file_obj = model.StorageFile(node=self.project)
        with assert_raises(modm_errors.ValidationError):
            file_obj.save()

    def test_get_download_path(self):
        file_obj = model.StorageFile(node=self.project, path=self.path)
        file_obj.save()
        version = 3
        assert_equal(
            file_obj.get_download_path(version),
            '/{0}/download/?version={1}&mode=render'.format(file_obj._id, version),
        )

    def test_get_or_create_exists(self):
        existing = model.StorageFile(node=self.project, path=self.path)
        existing.save()
        n_objs = model.StorageFile.find().count()
        result = model.StorageFile.get_or_create(self.project, self.path)
        assert_equal(result, existing)
        assert_equal(n_objs, model.StorageFile.find().count())

    def test_get_or_create_does_not_exist(self):
        n_objs = model.StorageFile.find().count()
        result = model.StorageFile.get_or_create(self.project, self.path)
        assert_equal(result.node, self.project)
        assert_equal(result.path, self.path)
        assert_equal(n_objs + 1, model.StorageFile.find().count())

