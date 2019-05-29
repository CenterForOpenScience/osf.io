# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import mock
from django.utils import timezone
from nose.tools import *  # noqa

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder, OsfStorageFileNode
from addons.s3.models import S3File
from osf.models import File
from osf.models import Folder
from osf.models.files import BaseFileNode
from tests.base import OsfTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory
from website.files import exceptions
from osf import models


class TestFileNode(BaseFileNode):
    _provider = 'test'


class TestFile(TestFileNode, File):
    pass


class TestFolder(TestFileNode, Folder):
    pass


class FilesTestCase(OsfTestCase):

    def setUp(self):
        super(FilesTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)


class TestStoredFileNode(FilesTestCase):

    def setUp(self):
        super(TestStoredFileNode, self).setUp()
        self.test_file = TestFile(
            _path='anid',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        self.test_file.save()

    def test_deep_url(self):
        url = self.test_file.deep_url
        assert_true(isinstance(url, basestring))
        assert_in(self.node._id, url)
        assert_in(self.test_file.path, url)
        assert_in(self.test_file.provider, url)

    def test_deep_url_unicode(self):
        self.test_file.path = u'༼ つ ͠° ͟ ͟ʖ ͡° ༽つ'
        self.test_file.save()
        url = self.test_file.deep_url
        assert_true(isinstance(url, basestring))
        assert_in(self.node._id, url)
        # Path is url encode
        # assert_in(self.sfn.path, url)
        assert_in(self.test_file.provider, url)

    def test_get_guid_no_create(self):
        assert_is(self.test_file.get_guid(), None)

    def test_get_guid_create(self):
        guid = self.test_file.get_guid(create=True)
        assert_equal(guid.referent, self.test_file)
        assert_equal(self.test_file.get_guid(), guid)


class TestFileNodeObj(FilesTestCase):

    def test_create(self):
        working = TestFile.create(name='myname')
        assert_equals(working.is_file, True)
        assert_equals(working.name, 'myname')
        assert_equals(working.provider, 'test')

    def test_get_or_create(self):
        created = TestFile.get_or_create(self.node, 'Path')
        created.name = 'kerp'
        created.materialized_path = 'crazypath'
        created.save()
        found = TestFile.get_or_create(self.node, '/Path')

        assert_equals(found.name, 'kerp')
        assert_equals(found.materialized_path, 'crazypath')

    def test_get_file_guids(self):
        created = TestFile.get_or_create(self.node, 'Path')
        created.name = 'kerp'
        created.materialized_path = '/Path'
        created.get_guid(create=True)
        created.save()
        file_guids = TestFile.get_file_guids(materialized_path=created.materialized_path,
                                             provider=created.provider,
                                             target=self.node)
        assert_in(created.get_guid()._id, file_guids)

    def test_get_file_guids_with_folder_path(self):
        created = TestFile.get_or_create(self.node, 'folder/Path')
        created.name = 'kerp'
        created.materialized_path = '/folder/Path'
        created.get_guid(create=True)
        created.save()
        file_guids = TestFile.get_file_guids(materialized_path='folder/',
                                             provider=created.provider,
                                             target=self.node)
        assert_in(created.get_guid()._id, file_guids)

    def test_get_file_guids_with_folder_path_does_not_include_deleted_files(self):
        created = TestFile.get_or_create(self.node, 'folder/Path')
        created.name = 'kerp'
        created.materialized_path = '/folder/Path'
        guid = created.get_guid(create=True)
        created.save()
        created.delete()
        file_guids = TestFile.get_file_guids(materialized_path='folder/',
                                             provider=created.provider,
                                             target=self.node)
        assert_not_in(guid._id, file_guids)

    def test_kind(self):
        assert_equals(TestFile().kind, 'file')
        assert_equals(TestFolder().kind, 'folder')

    def test_find(self):
        original_testfile_count = TestFile.objects.count()
        original_testfolder_count = TestFolder.objects.count()
        original_testfilenode_count = TestFileNode.objects.count()
        original_osfstoragefilenode_count = OsfStorageFileNode.objects.count()
        original_osfstoragefile_count= OsfStorageFile.objects.count()
        original_osfstoragefolder_count = OsfStorageFolder.objects.count()
        original_basefilenode_count = BaseFileNode.objects.count()

        TestFile.objects.create(
            _path='afile',
            name='name',
            target=self.node,
            materialized_path='/long/path/to/name',
        )

        TestFolder.objects.create(
            _path='afolder',
            name='name',
            target=self.node,
            materialized_path='/long/path/to/name2/',
        )

        assert_equal(TestFile.objects.count(), original_testfile_count + 1)
        assert_equal(TestFolder.objects.count(), original_testfolder_count + 1)
        assert_equal(TestFileNode.objects.count(), original_testfilenode_count + 2)
        assert_equal(OsfStorageFileNode.objects.count(), original_osfstoragefilenode_count)
        assert_equal(OsfStorageFile.objects.count(), original_osfstoragefile_count)
        assert_equal(OsfStorageFolder.objects.count(), original_osfstoragefolder_count)
        assert_equal(BaseFileNode.objects.count(), original_osfstoragefilenode_count + original_testfilenode_count + 2)  # roots of things

    def test_find_one(self):
        item = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        item.save()

        found = TestFile.objects.get(_path='afile')
        assert_true(isinstance(found, TestFile))
        assert_equal(found.materialized_path, '/long/path/to/name')

    def test_load(self):
        item = TestFolder(
            _path='afolder',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name2/',
        )
        item.save()

        assert_is(models.BaseFileNode.load('notanid'), None)
        assert_true(isinstance(TestFolder.load(item._id), TestFolder))
        assert_true(isinstance(models.BaseFileNode.load(item._id), TestFolder))

    def test_parent(self):
        parent = TestFolder(
            _path='afolder',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name2/',
        )
        parent.save()

        child = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        child.save()

        assert_is(child.parent, None)
        child.parent = parent
        child.save()
        assert_is(child.parent, parent)

    def test_save(self):
        child = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        assert_false(child._is_loaded)
        child.save()
        assert_true(child._is_loaded)

    def test_delete(self):
        tf = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            _materialized_path='/long/path/to/name',
        )

        tf.save()

        tf.delete()

        trashed = models.TrashedFile.objects.all()[0]
        assert_equal(trashed.path, 'afile')
        assert_equal(trashed.target, self.node)
        assert_equal(trashed.materialized_path, '/long/path/to/name')

    def test_delete_with_guid(self):
        tf = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        guid = tf.get_guid(create=True)
        tf.delete()

        trashed = models.TrashedFile.objects.all()[0]

        guid.reload()

        assert_equal(guid.referent, trashed)
        assert_equal(trashed.path, 'afile')
        assert_equal(trashed.target, self.node)
        assert_equal(trashed.materialized_path, '/long/path/to/name')
        assert_less((trashed.deleted_on - timezone.now()).total_seconds(), 5)

    def test_delete_with_user(self):
        fn = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        fn.delete(user=self.user)

        trashed = models.TrashedFileNode.objects.all()[0]
        assert_equal(trashed.deleted_by, self.user)
        assert_equal(TestFile.load(fn._id), None)

    def test_restore_file(self):
        root = TestFolder(
            _path='root',
            name='rootfolder',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to',
        )
        root.save()

        fn = TestFile(
            parent_id=root.id,
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        guid = fn.get_guid(create=True)

        trashed = fn.delete(user=self.user)

        restored = trashed.restore()

        local_django_fields = set([x.name for x in restored._meta.get_fields() if not x.is_relation])

        for field_name in local_django_fields:
            assert_equal(
                getattr(restored, field_name),
                getattr(fn, field_name)
            )

        assert_equal(models.TrashedFileNode.load(trashed._id), None)

        # Guid is repointed
        guid.reload()
        assert_equal(guid.referent, restored)

    def test_restore_folder(self):
        root = TestFolder.create(
            _path='root',
            name='rootfolder',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/',
        )
        root.save()

        fn = TestFile.create(
            parent_id=root.id,
            _path='afolder',
            name='folder_name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/folder_name',
        )
        fn.save()
        fn_id = fn._id
        trashed_root = root.delete(user=self.user)
        trashed_root_id = trashed_root._id

        restored = trashed_root.restore()

        local_django_fields = set([x.name for x in restored._meta.get_fields() if not x.is_relation])

        for field_name in local_django_fields:
            assert_equal(
                getattr(restored, field_name),
                getattr(root, field_name)
            )

        assert_equal(models.TrashedFileNode.load(trashed_root_id), None)
        assert_equal(models.TrashedFileNode.load(fn_id), None)

    def test_restore_folder_nested(self):
        def build_tree(acc=None, parent=None, atleastone=False):
            import random
            acc = acc or []
            if len(acc) > 5:
                return acc
            is_folder = atleastone
            for i in range(random.randrange(3, 15)):
                if is_folder:
                    fn = TestFolder(
                        _path='name{}'.format(i),
                        name='name{}'.format(i),
                        target=self.node,
                        parent_id=parent.id,
                        materialized_path='{}/{}'.format(parent.materialized_path, 'name{}'.format(i)),
                    )
                else:
                    fn = TestFile(
                        _path='name{}'.format(i),
                        name='name{}'.format(i),
                        target=self.node,
                        parent_id=parent.id,
                        materialized_path='{}/{}'.format(parent.materialized_path, 'name{}'.format(i)),
                    )

                fn.save()
                random.randint(0, 5) == 1
                if is_folder:
                    build_tree(acc, fn)
                acc.append(fn)
                is_folder = random.randint(0, 5) == 1
            return acc

        root = TestFolder(
            _path='root',
            name='rootfolder',
            target=self.node,
            materialized_path='/long/path/to/',
        )
        root.save()

        parent = TestFolder(
            parent_id=root.id,
            _path='afolder',
            name='folder_name',
            target=self.node,
            materialized_path='/long/path/to/folder_name',
        )
        parent.save()

        branch = TestFolder(
            _path='afolder',
            name='folder_name',
            target=self.node,
            parent_id=parent.id,
            materialized_path='/long/path/to/folder_name',
        )
        branch.save()

        round1 = build_tree(parent=branch, atleastone=True)
        round2 = build_tree(parent=parent, atleastone=True)

        stay_deleted = [branch.to_storage(include_auto_now=False)] + [child.to_storage(include_auto_now=False) for child in round1]
        get_restored = [parent.to_storage(include_auto_now=False)] + [child.to_storage(include_auto_now=False) for child in round2]

        branch.delete()

        for data in stay_deleted:
            assert_true(models.TrashedFileNode.load(data['_id']))
            assert_is(TestFileNode.load(data['_id']), None)

        trashed = parent.delete()

        for data in get_restored:
            assert_true(models.TrashedFileNode.load(data['_id']))
            assert_is(TestFileNode.load(data['_id']), None)

        trashed.restore()

        for data in stay_deleted:
            assert_true(models.TrashedFileNode.load(data['_id']))
            assert_is(TestFileNode.load(data['_id']), None)

        for data in get_restored:
            assert_is(models.TrashedFileNode.load(data['_id']), None)
            assert TestFileNode.load(data['_id']).to_storage(include_auto_now=False) == data

    def test_metadata_url(self):
        pass

    def test_move_under(self):
        pass

    def test_copy_under(self):
        pass

    def test_attr_passthrough(self):
        stored = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        stored.test = 'Foo'
        stored.bar = ['wat']
        wrapped = stored
        wrapped.bar.append('wat')

        assert_equal(stored.bar, wrapped.bar)
        assert_equal(stored.test, wrapped.test)

    def test_repr(self):
        child = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        assert_true(isinstance(child.__repr__(), basestring))


class TestFileObj(FilesTestCase):

    def test_get_version(self):
        v1 = models.FileVersion(identifier='1')
        v2 = models.FileVersion(identifier='2')
        v1.save()
        v2.save()

        file = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        file.save()

        file.versions.add(*[v1, v2])

        assert_equals(file.get_version('1'), v1)
        assert_equals(file.get_version('2', required=True), v2)

        assert_is(file.get_version('3'), None)

        with assert_raises(exceptions.VersionNotFoundError):
            file.get_version('3', required=True)

    def test_update_version_metadata(self):
        v1 = models.FileVersion(identifier='1')
        v1.save()

        file = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        file.save()

        file.versions.add(v1)
        file.update_version_metadata(None, {'size': 1337})

        with assert_raises(exceptions.VersionNotFoundError):
            file.update_version_metadata('3', {})
        v1.refresh_from_db()
        assert_equal(v1.size, 1337)

    @mock.patch('osf.models.files.requests.get')
    def test_touch(self, mock_requests):
        file = TestFile(
            _path='/afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        mock_requests.return_value = mock.Mock(status_code=400)
        assert_is(file.touch(None), None)

        mock_response = mock.Mock(status_code=200)
        mock_response.json.return_value = {
            'data': {
                'attributes': {
                    'name': 'fairly',
                    'modified': '2015',
                    'size': 0xDEADBEEF,
                    'materialized': 'ephemeral',
                }
            }
        }
        mock_requests.return_value = mock_response
        v = file.touch(None)
        assert_equals(v.size, 0xDEADBEEF)
        assert_equals(file.versions.count(), 0)

    @mock.patch('osf.models.files.requests.get')
    def test_touch_caching(self, mock_requests):
        file = TestFile(
            _path='/afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        mock_response = mock.Mock(status_code=200)
        mock_response.json.return_value = {
            'data': {
                'attributes': {
                    'name': 'fairly',
                    'modified': '2015',
                    'size': 0xDEADBEEF,
                    'materialized': 'ephemeral',
                }
            }
        }
        mock_requests.return_value = mock_response

        v = file.touch(None, revision='foo')
        assert_equals(file.versions.count(), 1)
        assert_equals(file.touch(None, revision='foo'), v)

    @mock.patch('osf.models.files.requests.get')
    def test_touch_auth(self, mock_requests):
        file = TestFile(
            _path='/afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        mock_response = mock.Mock(status_code=404)
        mock_requests.return_value = mock_response

        file.touch('Bearer bearer', revision='foo')
        assert_equal(mock_requests.call_args[1]['headers'], {
            'Authorization': 'Bearer bearer'
        })

    def test_download_url(self):
        pass

    def test_serialize(self):
        pass

    def test_get_download_count(self):
        pass


class TestFolderObj(FilesTestCase):

    def setUp(self):
        super(TestFolderObj, self).setUp()
        self.parent = TestFolder(
            _path='aparent',
            name='parent',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        self.parent.save()

    def test_children(self):
        TestFile(
            _path='afile',
            name='child',
            target=self.node,
            parent_id=self.parent.id,
            provider='test',
            materialized_path='/long/path/to/name',
        ).save()

        assert_equal(len(list(self.parent.children)), 1)

        TestFile(
            _path='afile2',
            name='child2',
            target=self.node,
            parent_id=self.parent.id,
            provider='test',
            materialized_path='/long/path/to/name',
        ).save()

        assert_equal(len(list(self.parent.children)), 2)

    def test_delete(self):
        child = TestFile(
            _path='afile',
            name='child',
            target=self.node,
            parent_id=self.parent.id,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        child.save()

        guid = self.parent.get_guid(create=True)
        child_guid = child.get_guid(create=True)
        trashed_parent = self.parent.delete(user=self.user)

        guid.reload()
        child_guid.reload()

        child = models.TrashedFileNode.load(child._id)
        prnt = child.parent

        assert_equal(
            trashed_parent,
            prnt
        )

        assert_equal(trashed_parent, guid.referent)
        assert_equal(child_guid.referent, models.TrashedFileNode.load(child._id))

    def test_append_file(self):
        self.parent.append_file('Name')
        (child, ) = list(self.parent.children)

    def test_append_folder(self):
        pass

    def test_find_child_by_name(self):
        pass


class TestFileVersion(FilesTestCase):
    pass


class TestSubclasses(FilesTestCase):

    @mock.patch('osf.models.BaseFileNode.touch')
    def test_s3file(self, mock_touch):
        file = S3File.create(
            _path='afile2',
            name='child2',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        file.touch(None)
        file.touch('bar', version='foo')
        file.touch(None, version='zyzz', bar='baz')

        mock_touch.assert_has_calls([
            mock.call(None),
            mock.call('bar', version='foo'),
            mock.call(None, version='zyzz', bar='baz'),
        ])
