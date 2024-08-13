import pytest
from unittest import mock
from django.utils import timezone

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder, OsfStorageFileNode
from addons.s3.models import S3File
from osf.models import BaseFileNode, File, Folder
from tests.base import OsfTestCase
import osf.models.files
from osf_tests.factories import AuthUserFactory, ProjectFactory
from website.files import exceptions
from website.files.utils import attach_versions
from osf import models


class TestFileNode(BaseFileNode):
    _provider = 'test'
    __test__ = False


class TestFile(TestFileNode, File):
    __test__ = False


class TestFolder(TestFileNode, Folder):
    __test__ = False


class FilesTestCase(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)


class TestStoredFileNode(FilesTestCase):

    def setUp(self):
        super().setUp()
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
        assert isinstance(url, str)
        assert self.node._id in url
        assert self.test_file.path in url
        assert self.test_file.provider in url

    def test_deep_url_unicode(self):
        self.test_file.path = '༼ つ ͠° ͟ ͟ʖ ͡° ༽つ'
        self.test_file.save()
        url = self.test_file.deep_url
        assert isinstance(url, str)
        assert self.node._id in url
        # Path is url encode
        # assert_in(self.sfn.path, url)
        assert self.test_file.provider in url

    def test_get_guid_no_create(self):
        assert self.test_file.get_guid() is None

    def test_get_guid_create(self):
        guid = self.test_file.get_guid(create=True)
        assert guid.referent == self.test_file
        assert self.test_file.get_guid() == guid


class TestFileNodeObj(FilesTestCase):

    def test_create(self):
        working = TestFile.create(name='myname')
        assert working.is_file == True
        assert working.name == 'myname'
        assert working.provider == 'test'

    def test_get_or_create(self):
        created = TestFile.get_or_create(self.node, 'Path')
        created.name = 'kerp'
        created.materialized_path = 'crazypath'
        created.save()
        found = TestFile.get_or_create(self.node, '/Path')

        assert found.name == 'kerp'
        assert found.materialized_path == 'crazypath'

    def test_get_file_guids(self):
        created = TestFile.get_or_create(self.node, 'Path')
        created.name = 'kerp'
        created.materialized_path = '/Path'
        created.get_guid(create=True)
        created.save()
        file_guids = TestFile.get_file_guids(materialized_path=created.materialized_path,
                                             provider=created.provider,
                                             target=self.node)
        assert created.get_guid()._id in file_guids

    def test_get_file_guids_with_folder_path(self):
        created = TestFile.get_or_create(self.node, 'folder/Path')
        created.name = 'kerp'
        created.materialized_path = '/folder/Path'
        created.get_guid(create=True)
        created.save()
        file_guids = TestFile.get_file_guids(materialized_path='folder/',
                                             provider=created.provider,
                                             target=self.node)
        assert created.get_guid()._id in file_guids

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
        assert guid._id not in file_guids

    def test_kind(self):
        assert TestFile().kind == 'file'
        assert TestFolder().kind == 'folder'

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

        assert TestFile.objects.count() == original_testfile_count + 1
        assert TestFolder.objects.count() == original_testfolder_count + 1
        assert TestFileNode.objects.count() == original_testfilenode_count + 2
        assert OsfStorageFileNode.objects.count() == original_osfstoragefilenode_count
        assert OsfStorageFile.objects.count() == original_osfstoragefile_count
        assert OsfStorageFolder.objects.count() == original_osfstoragefolder_count
        assert BaseFileNode.objects.count() == original_osfstoragefilenode_count + original_testfilenode_count + 2  # roots of things

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
        assert isinstance(found, TestFile)
        assert found.materialized_path == '/long/path/to/name'

    def test_load(self):
        item = TestFolder(
            _path='afolder',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name2/',
        )
        item.save()

        assert models.BaseFileNode.load('notanid') is None
        assert isinstance(TestFolder.load(item._id), TestFolder)
        assert isinstance(models.BaseFileNode.load(item._id), TestFolder)

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

        assert child.parent is None
        child.parent = parent
        child.save()
        assert child.parent is parent

    def test_save(self):
        child = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        assert not child._is_loaded
        child.save()
        assert child._is_loaded

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
        assert trashed.path == 'afile'
        assert trashed.target == self.node
        assert trashed.materialized_path == '/long/path/to/name'

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

        assert guid.referent == trashed
        assert trashed.path == 'afile'
        assert trashed.target == self.node
        assert trashed.materialized_path == '/long/path/to/name'
        difference_seconds = (trashed.deleted_on - timezone.now()).total_seconds()
        assert difference_seconds < 5

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
        assert trashed.deleted_by == self.user
        assert TestFile.load(fn._id) is None

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

        local_django_fields = {x.name for x in restored._meta.get_fields() if not x.is_relation}

        for field_name in local_django_fields:
            assert getattr(restored, field_name) == getattr(fn, field_name)

        assert models.TrashedFileNode.load(trashed._id) is None

        # Guid is repointed
        guid.reload()
        assert guid.referent == restored

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

        local_django_fields = {x.name for x in restored._meta.get_fields() if not x.is_relation}

        for field_name in local_django_fields:
            assert getattr(restored, field_name) == getattr(root, field_name)

        assert models.TrashedFileNode.load(trashed_root_id) is None
        assert models.TrashedFileNode.load(fn_id) is None

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
                        _path=f'name{i}',
                        name=f'name{i}',
                        target=self.node,
                        parent_id=parent.id,
                        materialized_path='{}/{}'.format(parent.materialized_path, f'name{i}'),
                    )
                else:
                    fn = TestFile(
                        _path=f'name{i}',
                        name=f'name{i}',
                        target=self.node,
                        parent_id=parent.id,
                        materialized_path='{}/{}'.format(parent.materialized_path, f'name{i}'),
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
            assert models.TrashedFileNode.load(data['_id'])
            assert TestFileNode.load(data['_id']) is None

        trashed = parent.delete()

        for data in get_restored:
            assert models.TrashedFileNode.load(data['_id'])
            assert TestFileNode.load(data['_id']) is None

        trashed.restore()

        for data in stay_deleted:
            assert models.TrashedFileNode.load(data['_id'])
            assert TestFileNode.load(data['_id']) is None

        for data in get_restored:
            assert models.TrashedFileNode.load(data['_id']) is None
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

        assert stored.bar == wrapped.bar
        assert stored.test == wrapped.test

    def test_repr(self):
        child = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        assert isinstance(child.__repr__(), str)


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

        attach_versions(file, [v1, v2])

        assert file.get_version('1') == v1
        assert file.get_version('2', required=True) == v2

        assert file.get_version('3') is None

        with pytest.raises(exceptions.VersionNotFoundError):
            file.get_version('3', required=True)

    def test_update_version_metadata(self):
        location = {
            'service': 'cloud',
            'folder': 'osf',
            'object': 'file',
        }
        v1 = models.FileVersion(identifier='1', location=location)
        v1.save()

        file = TestFile(
            _path='afile',
            name='name',
            target=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )

        file.save()
        file.add_version(v1)
        assert v1 == file.versions.get()

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
        assert file.touch(None) is None

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
        assert v.size == 0xDEADBEEF
        assert file.versions.count() == 0

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
        assert file.versions.count() == 1
        assert file.touch(None, revision='foo') == v

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
        assert mock_requests.call_args[1]['headers'] == {
            'Authorization': 'Bearer bearer'
        }

    def test_download_url(self):
        pass

    def test_serialize(self):
        pass

    def test_get_download_count(self):
        pass


class TestFolderObj(FilesTestCase):

    def setUp(self):
        super().setUp()
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

        assert len(list(self.parent.children)) == 1

        TestFile(
            _path='afile2',
            name='child2',
            target=self.node,
            parent_id=self.parent.id,
            provider='test',
            materialized_path='/long/path/to/name',
        ).save()

        assert len(list(self.parent.children)) == 2

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

        assert trashed_parent == prnt

        assert trashed_parent == guid.referent
        assert child_guid.referent == models.TrashedFileNode.load(child._id)

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
