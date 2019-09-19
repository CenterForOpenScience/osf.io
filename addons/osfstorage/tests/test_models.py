from __future__ import unicode_literals

import mock
import unittest

import pytest
import pytz
from django.utils import timezone
from nose.tools import *  # noqa

from framework.auth import Auth
from addons.osfstorage.models import OsfStorageFile, OsfStorageFileNode, OsfStorageFolder
from osf.exceptions import ValidationError
from osf.utils.permissions import WRITE, ADMIN
from osf.utils.fields import EncryptedJSONField
from osf_tests.factories import ProjectFactory, UserFactory, PreprintFactory, RegionFactory, NodeFactory

from addons.osfstorage.tests import factories
from addons.osfstorage.tests.utils import StorageTestCase
from addons.osfstorage.listeners import delete_files_task

import datetime

from osf import models
from addons.osfstorage import utils
from addons.osfstorage import settings
from website.files.exceptions import FileNodeCheckedOutError, FileNodeIsPrimaryFile


@pytest.mark.django_db
class TestOsfstorageFileNode(StorageTestCase):
    def test_root_node_exists(self):
        assert_true(self.node_settings.root_node is not None)

    def test_root_node_has_no_parent(self):
        assert_true(self.node_settings.root_node.parent is None)

    def test_node_reference(self):
        assert_equal(self.project, self.node_settings.root_node.target)

    # def test_get_folder(self):
    #     file = models.OsfStorageFile(name='MOAR PYLONS', node=self.node)
    #     folder = models.OsfStorageFolder(name='MOAR PYLONS', node=self.node)

    #     _id = folder._id

    #     file.save()
    #     folder.save()

    #     assert_equal(folder, models.OsfStorageFileNode.get_folder(_id, self.node_settings))

    # def test_get_file(self):
    #     file = models.OsfStorageFile(name='MOAR PYLONS', node=self.node)
    #     folder = models.OsfStorageFolder(name='MOAR PYLONS', node=self.node)

    #     file.save()
    #     folder.save()

    #     _id = file._id

    #     assert_equal(file, models.OsfStorageFileNode.get_file(_id, self.node_settings))

    def test_serialize(self):
        file = OsfStorageFile(name='MOAR PYLONS', target=self.node_settings.owner)
        file.save()

        assert_equals(file.serialize(), {
            u'id': file._id,
            u'path': file.path,
            u'created': None,
            u'name': u'MOAR PYLONS',
            u'kind': 'file',
            u'version': 0,
            u'downloads': 0,
            u'size': None,
            u'modified': None,
            u'contentType': None,
            u'checkout': None,
            u'md5': None,
            u'sha256': None,
        })

        version = file.create_version(
            self.user,
            {
                u'service': u'cloud',
                settings.WATERBUTLER_RESOURCE: u'osf',
                u'object': u'06d80e',
            }, {
                u'size': 1234,
                u'contentType': u'text/plain'
            })

        assert_equals(file.serialize(), {
            u'id': file._id,
            u'path': file.path,
            u'created': version.created.isoformat(),
            u'name': u'MOAR PYLONS',
            u'kind': u'file',
            u'version': 1,
            u'downloads': 0,
            u'size': 1234L,
            u'modified': version.created.isoformat(),
            u'contentType': u'text/plain',
            u'checkout': None,
            u'md5': None,
            u'sha256': None,
        })

        date = timezone.now()
        version.update_metadata({
            u'modified': date.isoformat()
        })

        assert_equals(file.serialize(), {
            u'id': file._id,
            u'path': file.path,
            u'created': version.created.isoformat(),
            u'name': u'MOAR PYLONS',
            u'kind': u'file',
            u'version': 1,
            u'downloads': 0,
            u'size': 1234L,
            # modified date is the creation date of latest version
            # see https://github.com/CenterForOpenScience/osf.io/pull/7155
            u'modified': version.created.isoformat(),
            u'contentType': u'text/plain',
            u'checkout': None,
            u'md5': None,
            u'sha256': None,
        })

    def test_get_child_by_name(self):
        child = self.node_settings.get_root().append_file('Test')
        assert_equal(child, self.node_settings.get_root().find_child_by_name('Test'))

    def test_root_node_path(self):
        assert_equal(self.node_settings.get_root().name, '')

    def test_folder_path(self):
        path = '/{}/'.format(self.node_settings.root_node._id)

        assert_equal(self.node_settings.get_root().path, path)

    def test_file_path(self):
        file = OsfStorageFile(name='MOAR PYLONS', target=self.node)
        file.save()
        assert_equal(file.name, 'MOAR PYLONS')
        assert_equal(file.path, '/{}'.format(file._id))

    def test_append_folder(self):
        child = self.node_settings.get_root().append_folder('Test')
        children = self.node_settings.get_root().children

        assert_equal(child.kind, 'folder')
        assert_equal([child], list(children))

    def test_append_file(self):
        child = self.node_settings.get_root().append_file('Test')
        children = self.node_settings.get_root().children

        assert_equal(child.kind, 'file')
        assert_equal([child], list(children))

    def test_append_to_file(self):
        child = self.node_settings.get_root().append_file('Test')
        with assert_raises(AttributeError):
            child.append_file('Cant')

    def test_children(self):
        kids = [
            self.node_settings.get_root().append_file('Foo{}Bar'.format(x))
            for x in range(100)
        ]

        assert_equals(sorted(kids, key=lambda kid: kid.name), list(self.node_settings.get_root().children.order_by('name')))

    def test_download_count_file_defaults(self):
        child = self.node_settings.get_root().append_file('Test')
        assert_equals(child.get_download_count(), 0)

    @mock.patch('framework.sessions.session')
    def test_download_count_file(self, mock_session):
        mock_session.data = {}
        child = self.node_settings.get_root().append_file('Test')

        utils.update_analytics(self.project, child._id, 0)
        utils.update_analytics(self.project, child._id, 1)
        utils.update_analytics(self.project, child._id, 2)

        assert_equals(child.get_download_count(), 3)
        assert_equals(child.get_download_count(0), 1)
        assert_equals(child.get_download_count(1), 1)
        assert_equals(child.get_download_count(2), 1)

    @unittest.skip
    def test_create_version(self):
        pass

    @unittest.skip
    def test_update_version_metadata(self):
        pass

    def test_delete_folder(self):
        parent = self.node_settings.get_root().append_folder('Test')
        kids = []
        for x in range(10):
            kid = parent.append_file(str(x))
            kid.save()
            kids.append(kid)
        count = OsfStorageFileNode.objects.count()
        tcount = models.TrashedFileNode.objects.count()

        parent.delete()

        assert_is(OsfStorageFileNode.load(parent._id), None)
        assert_equals(count - 11, OsfStorageFileNode.objects.count())
        assert_equals(tcount + 11, models.TrashedFileNode.objects.count())

        for kid in kids:
            assert_is(
                OsfStorageFileNode.load(kid._id),
                None
            )

    def test_delete_file(self):
        child = self.node_settings.get_root().append_file('Test')
        field_names = [f.name for f in child._meta.get_fields() if not f.is_relation and f.name not in ['id', 'content_type_pk']]
        child_data = {f: getattr(child, f) for f in field_names}
        child.delete()

        assert_is(OsfStorageFileNode.load(child._id), None)
        trashed = models.TrashedFileNode.load(child._id)
        child_storage = dict()
        trashed_storage = dict()
        trashed_storage['parent'] = trashed.parent._id
        child_storage['materialized_path'] = child.materialized_path
        assert_equal(trashed.path, '/' + child._id)
        trashed_field_names = [f.name for f in child._meta.get_fields() if not f.is_relation and
                               f.name not in ['id', '_materialized_path', 'content_type_pk', '_path', 'deleted_on', 'deleted_by', 'type', 'modified']]
        for f, value in child_data.items():
            if f in trashed_field_names:
                assert_equal(getattr(trashed, f), value)

    def test_delete_preprint_primary_file(self):
        user = UserFactory()
        preprint = PreprintFactory(creator=user)
        preprint.save()
        file = preprint.files.all()[0]

        with assert_raises(FileNodeIsPrimaryFile):
            file.delete()

    def test_delete_file_no_guid(self):
        child = self.node_settings.get_root().append_file('Test')

        assert_is(OsfStorageFileNode.load(child._id).guids.first(), None)

        with mock.patch('osf.models.files.apps.get_model') as get_model:
            child.delete()

            assert_is(get_model.called, False)

        assert_is(OsfStorageFileNode.load(child._id), None)

    def test_delete_file_guids(self):
        child = self.node_settings.get_root().append_file('Test')
        guid = child.get_guid(create=True)

        assert_is_not(OsfStorageFileNode.load(child._id).guids.first(), None)

        with mock.patch('osf.models.files.apps.get_model') as get_model:
            child.delete()

            assert_is(get_model.called, True)
            assert_is(get_model('osf.Comment').objects.filter.called, True)

        assert_is(OsfStorageFileNode.load(child._id), None)

    @mock.patch('addons.osfstorage.listeners.enqueue_postcommit_task')
    def test_file_deleted_when_node_deleted(self, mock_enqueue):
        child = self.node_settings.get_root().append_file('Test')
        self.node.remove_node(auth=Auth(self.user))

        mock_enqueue.assert_called_with(delete_files_task, (self.node._id, ), {}, celery=True)

    def test_materialized_path(self):
        child = self.node_settings.get_root().append_file('Test')
        assert_equals('/Test', child.materialized_path)

    def test_materialized_path_folder(self):
        child = self.node_settings.get_root().append_folder('Test')
        assert_equals('/Test/', child.materialized_path)

    def test_materialized_path_nested(self):
        child = self.node_settings.get_root().append_folder('Cloud').append_file('Carp')
        assert_equals('/Cloud/Carp', child.materialized_path)

    def test_copy(self):
        to_copy = self.node_settings.get_root().append_file('Carp')
        copy_to = self.node_settings.get_root().append_folder('Cloud')
        version = to_copy.create_version(
            self.user,
            {
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': '06d80e',
            }, {
                'sha256': 'existing',
                'vault': 'the cloud',
                'archive': 'erchiv'
            })
        assert_equal(to_copy.versions.first().get_basefilenode_version(to_copy).version_name, 'Carp')

        copied = to_copy.copy_under(copy_to)

        assert_not_equal(copied, to_copy)
        assert_equal(copied.parent, copy_to)
        assert_equal(copied.versions.first().get_basefilenode_version(copied).version_name, 'Carp')
        assert_equal(to_copy.parent, self.node_settings.get_root())

    def test_copy_node_file_to_preprint(self):
        user = UserFactory()
        preprint = PreprintFactory(creator=user)
        preprint.save()

        to_copy = self.node_settings.get_root().append_file('Carp')
        copy_to = preprint.root_folder

        copied = to_copy.copy_under(copy_to)
        assert_equal(copied.parent, copy_to)
        assert_equal(copied.target, preprint)

    def test_move_nested(self):
        new_project = ProjectFactory()
        other_node_settings = new_project.get_addon('osfstorage')
        move_to = other_node_settings.get_root().append_folder('Cloud')

        to_move = self.node_settings.get_root().append_folder('Carp')
        child = to_move.append_file('A dee um')

        moved = to_move.move_under(move_to)
        child.reload()

        assert_equal(moved, to_move)
        assert_equal(new_project, to_move.target)
        assert_equal(new_project, move_to.target)
        assert_equal(new_project, child.target)

    def test_move_nested_between_regions(self):
        canada = RegionFactory()
        new_component = NodeFactory(parent=self.project)
        component_node_settings = new_component.get_addon('osfstorage')
        component_node_settings.region = canada
        component_node_settings.save()

        move_to = component_node_settings.get_root()
        to_move = self.node_settings.get_root().append_folder('Aaah').append_folder('Woop')
        child = to_move.append_file('There it is')

        for _ in range(2):
            version = factories.FileVersionFactory(region=self.node_settings.region)
            child.add_version(version)
        child.save()

        moved = to_move.move_under(move_to)
        child.reload()

        assert new_component == child.target
        versions = child.versions.order_by('-created')
        assert versions.first().region == component_node_settings.region
        assert versions.last().region == self.node_settings.region

    def test_copy_rename(self):
        to_copy = self.node_settings.get_root().append_file('Carp')
        copy_to = self.node_settings.get_root().append_folder('Cloud')
        version = to_copy.create_version(
            self.user,
            {
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': '06d80e',
            }, {
                'sha256': 'existing',
                'vault': 'the cloud',
                'archive': 'erchiv'
            })
        assert_equal(to_copy.versions.first().get_basefilenode_version(to_copy).version_name, 'Carp')

        copied = to_copy.copy_under(copy_to, name='But')
        assert_equal(copied.versions.first().get_basefilenode_version(copied).version_name, 'But')

        assert_equal(copied.name, 'But')
        assert_not_equal(copied, to_copy)
        assert_equal(to_copy.name, 'Carp')
        assert_equal(copied.parent, copy_to)
        assert_equal(to_copy.parent, self.node_settings.get_root())

    def test_move(self):
        to_move = self.node_settings.get_root().append_file('Carp')
        move_to = self.node_settings.get_root().append_folder('Cloud')

        moved = to_move.move_under(move_to)

        assert_equal(to_move, moved)
        assert_equal(moved.parent, move_to)

    def test_move_and_rename(self):
        to_move = self.node_settings.get_root().append_file('Carp')
        version = to_move.create_version(
            self.user,
            {
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': '06d80e',
            }, {
                'sha256': 'existing',
                'vault': 'the cloud',
                'archive': 'erchiv'
            })
        move_to = self.node_settings.get_root().append_folder('Cloud')
        assert_equal(to_move.versions.first().get_basefilenode_version(to_move).version_name, 'Carp')

        moved = to_move.move_under(move_to, name='Tuna')

        assert_equal(to_move, moved)
        assert_equal(to_move.name, 'Tuna')
        assert_equal(moved.versions.first().get_basefilenode_version(moved).version_name, 'Tuna')
        assert_equal(moved.parent, move_to)

    def test_move_preprint_primary_file_to_node(self):
        user = UserFactory()
        preprint = PreprintFactory(creator=user)
        preprint.save()
        to_move = preprint.files.all()[0]
        assert_true(to_move.is_preprint_primary)

        move_to = self.node_settings.get_root().append_folder('Cloud')
        with assert_raises(FileNodeIsPrimaryFile):
            moved = to_move.move_under(move_to, name='Tuna')

    def test_move_preprint_primary_file_within_preprint(self):
        user = UserFactory()
        preprint = PreprintFactory(creator=user)
        preprint.save()
        folder = OsfStorageFolder(name='foofolder', target=preprint)
        folder.save()

        to_move = preprint.files.all()[0]
        assert_true(to_move.is_preprint_primary)

        moved = to_move.move_under(folder, name='Tuna')
        assert preprint.primary_file == to_move
        assert to_move.parent == folder
        assert folder.target == preprint

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

    def test_get_file_guids_for_live_file(self):
        node = self.node_settings.owner
        file = OsfStorageFile(name='foo', target=node)
        file.save()

        file.get_guid(create=True)
        guid = file.get_guid()._id

        assert guid is not None
        assert guid in OsfStorageFileNode.get_file_guids(
            '/' + file._id, provider='osfstorage', target=node)

    def test_get_file_guids_for_live_folder(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))
            files[-1].get_guid(create=True)

        guids = [file.get_guid()._id for file in files]
        assert len(guids) == len(files)

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert sorted(guids) == sorted(all_guids)

    def test_get_file_guids_for_trashed_file(self):
        node = self.node_settings.owner
        file = OsfStorageFile(name='foo', target=node)
        file.save()

        file.get_guid(create=True)
        guid = file.get_guid()._id

        file.delete()
        assert guid is not None
        assert guid in OsfStorageFileNode.get_file_guids(
            '/' + file._id, provider='osfstorage', target=node)

    def test_get_file_guids_for_trashed_folder(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))
            files[-1].get_guid(create=True)

        guids = [file.get_guid()._id for file in files]
        assert len(guids) == len(files)

        folder.delete()

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert sorted(guids) == sorted(all_guids)

    def test_get_file_guids_live_file_wo_guid(self):
        node = self.node_settings.owner
        file = OsfStorageFile(name='foo', target=node)
        file.save()
        assert [] == OsfStorageFileNode.get_file_guids(
            '/' + file._id, provider='osfstorage', target=node)

    def test_get_file_guids_for_live_folder_wo_guids(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert [] == all_guids

    def test_get_file_guids_trashed_file_wo_guid(self):
        node = self.node_settings.owner
        file = OsfStorageFile(name='foo', target=node)
        file.save()
        file.delete()
        assert [] == OsfStorageFileNode.get_file_guids(
            '/' + file._id, provider='osfstorage', target=node)

    def test_get_file_guids_for_trashed_folder_wo_guids(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))

        folder.delete()

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert [] == all_guids

    def test_get_file_guids_for_live_folder_recursive(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))
            files[-1].get_guid(create=True)

        subfolder = folder.append_folder('subfoo')
        for i in range(1, 4):
            files.append(subfolder.append_file('subfoo.{}'.format(i)))
            files[-1].get_guid(create=True)

        guids = [file.get_guid()._id for file in files]
        assert len(guids) == len(files)

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert sorted(guids) == sorted(all_guids)

    def test_get_file_guids_for_trashed_folder_recursive(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))
            files[-1].get_guid(create=True)

        subfolder = folder.append_folder('subfoo')
        for i in range(1, 4):
            files.append(subfolder.append_file('subfoo.{}'.format(i)))
            files[-1].get_guid(create=True)

        guids = [file.get_guid()._id for file in files]
        assert len(guids) == len(files)

        folder.delete()

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert sorted(guids) == sorted(all_guids)

    def test_get_file_guids_for_live_folder_recursive_wo_guids(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))

        subfolder = folder.append_folder('subfoo')
        for i in range(1, 4):
            files.append(subfolder.append_file('subfoo.{}'.format(i)))

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert [] == all_guids

    def test_get_file_guids_for_trashed_folder_recursive_wo_guids(self):
        node = self.node_settings.owner
        folder = OsfStorageFolder(name='foofolder', target=node)
        folder.save()

        files = []
        for i in range(1, 4):
            files.append(folder.append_file('foo.{}'.format(i)))

        subfolder = folder.append_folder('subfoo')
        for i in range(1, 4):
            files.append(subfolder.append_file('subfoo.{}'.format(i)))

        folder.delete()

        all_guids = OsfStorageFileNode.get_file_guids(
            '/' + folder._id, provider='osfstorage', target=node)
        assert [] == all_guids


@pytest.mark.django_db
class TestNodeSettingsModel(StorageTestCase):
    def test_fields(self):
        assert_true(self.node_settings._id)
        assert_is(self.node_settings.has_auth, True)
        assert_is(self.node_settings.complete, True)

    def test_after_fork_copies_versions(self):
        num_versions = 5
        path = 'jazz/dreamers-ball.mp3'

        record = self.node_settings.get_root().append_file(path)

        for _ in range(num_versions):
            version = factories.FileVersionFactory()
            record.add_version(version)

        fork = self.project.fork_node(self.auth_obj)
        fork_node_settings = fork.get_addon('osfstorage')
        fork_node_settings.reload()

        cloned_record = fork_node_settings.get_root().find_child_by_name(path)
        assert_equal(list(cloned_record.versions.all()), list(record.versions.all()))
        assert_true(fork_node_settings.root_node)

    def test_fork_reverts_to_using_user_storage_default(self):
        user = UserFactory()
        user2 = UserFactory()
        us = RegionFactory()
        canada = RegionFactory()

        user_settings = user.get_addon('osfstorage')
        user_settings.default_region = us
        user_settings.save()
        user2_settings = user2.get_addon('osfstorage')
        user2_settings.default_region = canada
        user2_settings.save()

        project = ProjectFactory(creator=user, is_public=True)
        child = NodeFactory(parent=project, creator=user, is_public=True)
        child_settings = child.get_addon('osfstorage')
        child_settings.region_id = canada.id
        child_settings.save()

        fork = project.fork_node(Auth(user))
        child_fork = models.Node.objects.get_children(fork).first()
        assert fork.get_addon('osfstorage').region_id == us.id
        assert fork.get_addon('osfstorage').user_settings == user.get_addon('osfstorage')
        assert child_fork.get_addon('osfstorage').region_id == us.id

        fork = project.fork_node(Auth(user2))
        child_fork = models.Node.objects.get_children(fork).first()
        assert fork.get_addon('osfstorage').region_id == canada.id
        assert fork.get_addon('osfstorage').user_settings == user2.get_addon('osfstorage')
        assert child_fork.get_addon('osfstorage').region_id == canada.id

    def test_region_wb_url_from_creators_defaults(self):
        user = UserFactory()
        region = RegionFactory()

        user_settings = user.get_addon('osfstorage')
        user_settings.default_region = region
        user_settings.save()

        project = ProjectFactory(creator=user)
        node_settings = project.get_addon('osfstorage')

        assert node_settings.region_id == region.id

    def test_encrypted_json_field(self):
        new_test_creds = {
            'storage': {
                'go': 'science',
                'hey': ['woo', 'yeah', 'great']
            }
        }
        region = RegionFactory()
        region.waterbutler_credentials = new_test_creds
        region.save()

        assert region.waterbutler_credentials == new_test_creds


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestOsfStorageFileVersion(StorageTestCase):
    def setUp(self):
        super(TestOsfStorageFileVersion, self).setUp()
        self.user = factories.AuthUserFactory()
        self.mock_date = datetime.datetime(1991, 10, 31, tzinfo=pytz.UTC)

    def test_fields(self):
        version = factories.FileVersionFactory(
            size=1024,
            content_type='application/json',
            modified=timezone.now(),
        )
        retrieved = models.FileVersion.load(version._id)
        assert_true(retrieved.creator)
        assert_true(retrieved.location)
        assert_true(retrieved.size)
        # sometimes identifiers are strings, so this always has to be a string, sql is funny about that.
        assert_equal(retrieved.identifier, u'0')
        assert_true(retrieved.content_type)
        assert_true(retrieved.modified)

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
        creator = factories.AuthUserFactory()
        version = factories.FileVersionFactory.build(creator=creator, location={'invalid': True})
        with assert_raises(ValidationError):
            version.save()
        version.location = {
            'service': 'cloud',
            settings.WATERBUTLER_RESOURCE: 'osf',
            'object': 'object',
        }
        version.save()

    def test_update_metadata(self):
        version = factories.FileVersionFactory()
        version.update_metadata(
            {'archive': 'glacier', 'size': 123, 'modified': 'Mon, 16 Feb 2015 18:45:34 GMT'})
        version.reload()
        assert_in('archive', version.metadata)
        assert_equal(version.metadata['archive'], 'glacier')

    def test_matching_archive(self):
        version = factories.FileVersionFactory(
            location={
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': 'd077f2',
            },
            metadata={'sha256': 'existing'}
        )
        factories.FileVersionFactory(
            location={
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': '06d80e',
            },
            metadata={
                'sha256': 'existing',
                'vault': 'the cloud',
                'archive': 'erchiv'
            }
        )

        assert_is(version._find_matching_archive(), True)
        assert_is_not(version.archive, None)

        assert_equal(version.metadata['vault'], 'the cloud')
        assert_equal(version.metadata['archive'], 'erchiv')

    def test_archive_exits(self):
        node_addon = self.project.get_addon('osfstorage')
        fnode = node_addon.get_root().append_file('MyCoolTestFile')
        version = fnode.create_version(
            self.user,
            {
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': '06d80e',
            }, {
                'sha256': 'existing',
                'vault': 'the cloud',
                'archive': 'erchiv'
            })

        assert_equal(version.archive, 'erchiv')

        version2 = fnode.create_version(
            self.user,
            {
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': '07d80a',
            }, {
                'sha256': 'existing',
            })

        assert_equal(version2.archive, 'erchiv')

    def test_no_matching_archive(self):
        models.FileVersion.objects.all().delete()
        assert_is(False, factories.FileVersionFactory(
            location={
                'service': 'cloud',
                settings.WATERBUTLER_RESOURCE: 'osf',
                'object': 'd077f2',
            },
            metadata={'sha256': 'existing'}
        )._find_matching_archive())


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestOsfStorageCheckout(StorageTestCase):
    def setUp(self):
        super(TestOsfStorageCheckout, self).setUp()
        self.user = factories.AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.osfstorage = self.node.get_addon('osfstorage')
        self.root_node = self.osfstorage.get_root()
        self.file = self.root_node.append_file('3005')

    def test_checkout_logs(self):
        non_admin = factories.AuthUserFactory()
        self.node.add_contributor(non_admin, permissions=WRITE)
        self.node.save()
        self.file.check_in_or_out(non_admin, non_admin, save=True)
        self.file.reload()
        self.node.reload()
        assert_equal(self.file.checkout, non_admin)
        assert_equal(self.node.logs.latest().action, 'checked_out')
        assert_equal(self.node.logs.latest().user, non_admin)

        self.file.check_in_or_out(self.user, None, save=True)
        self.file.reload()
        self.node.reload()
        assert_equal(self.file.checkout, None)
        assert_equal(self.node.logs.latest().action, 'checked_in')
        assert_equal(self.node.logs.latest().user, self.user)

        self.file.check_in_or_out(self.user, self.user, save=True)
        self.file.reload()
        self.node.reload()
        assert_equal(self.file.checkout, self.user)
        assert_equal(self.node.logs.latest().action, 'checked_out')
        assert_equal(self.node.logs.latest().user, self.user)

        with assert_raises(FileNodeCheckedOutError):
            self.file.check_in_or_out(non_admin, None, save=True)

        with assert_raises(FileNodeCheckedOutError):
            self.file.check_in_or_out(non_admin, non_admin, save=True)

    def test_delete_checked_out_file(self):
        self.file.check_in_or_out(self.user, self.user, save=True)
        self.file.reload()
        assert_equal(self.file.checkout, self.user)
        with assert_raises(FileNodeCheckedOutError):
            self.file.delete()

    def test_delete_folder_with_checked_out_file(self):
        folder = self.root_node.append_folder('folder')
        self.file.move_under(folder)
        self.file.check_in_or_out(self.user, self.user, save=True)
        self.file.reload()
        assert_equal(self.file.checkout, self.user)
        with assert_raises(FileNodeCheckedOutError):
            folder.delete()

    def test_move_checked_out_file(self):
        self.file.check_in_or_out(self.user, self.user, save=True)
        self.file.reload()
        assert_equal(self.file.checkout, self.user)
        folder = self.root_node.append_folder('folder')
        with assert_raises(FileNodeCheckedOutError):
            self.file.move_under(folder)

    def test_checked_out_merge(self):
        user = factories.AuthUserFactory()
        node = ProjectFactory(creator=user)
        osfstorage = node.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        file = root_node.append_file('test_file')
        user_merge_target = factories.AuthUserFactory()
        file.check_in_or_out(user, user, save=True)
        file.reload()
        assert_equal(file.checkout, user)
        user_merge_target.merge_user(user)
        file.reload()
        assert_equal(user_merge_target.id, file.checkout.id)

    def test_remove_contributor_with_checked_file(self):
        user = factories.AuthUserFactory()
        models.Contributor.objects.create(
            node=self.node,
            user=user,
            visible=True
        )
        self.node.add_permission(user, ADMIN)
        self.file.check_in_or_out(self.user, self.user, save=True)
        self.file.reload()
        assert_equal(self.file.checkout, self.user)
        self.file.target.remove_contributors([self.user], save=True)
        self.file.reload()
        assert_equal(self.file.checkout, None)
