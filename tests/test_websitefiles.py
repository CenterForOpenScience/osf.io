# -*- coding: utf-8 -*-
import mock
import datetime
from nose.tools import *  # noqa
from modularodm import Q
from website.files import utils
from website.files import models
from website.files import exceptions

from tests.base import OsfTestCase
from tests.factories import AuthUserFactory, ProjectFactory


class TestFileNode(models.FileNode):
    provider = 'test'


class TestFile(models.File, TestFileNode):
    pass


class TestFolder(models.Folder, TestFileNode):
    pass


class FilesTestCase(OsfTestCase):

    def setUp(self):
        super(FilesTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def tearDown(self):
        super(FilesTestCase, self).setUp()
        models.StoredFileNode.remove()
        models.TrashedFileNode.remove()


class TestFileNodeMeta(FilesTestCase):

    def test_conflicting_providers(self):

        with assert_raises(ValueError) as e:
            class Two(models.FileNode):
                is_file = True
                provider = 'test'

        assert_equal(e.exception.message, 'Conflicting providers')


class TestStoredFileNode(FilesTestCase):

    def setUp(self):
        super(TestStoredFileNode, self).setUp()
        self.sfn = models.StoredFileNode(
            path='anid',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        self.sfn.save()

    def test_deep_url(self):
        url = self.sfn.deep_url
        assert_true(isinstance(url, basestring))
        assert_in(self.node._id, url)
        assert_in(self.sfn.path, url)
        assert_in(self.sfn.provider, url)

    def test_deep_url_unicode(self):
        self.sfn.path = u'༼ つ ͠° ͟ ͟ʖ ͡° ༽つ'
        self.sfn.save()
        url = self.sfn.deep_url
        assert_true(isinstance(url, basestring))
        assert_in(self.node._id, url)
        # Path is url encode
        # assert_in(self.sfn.path, url)
        assert_in(self.sfn.provider, url)

    def test_wrapped(self):
        assert_true(isinstance(self.sfn.wrapped(), TestFile))

    def test_wrapped_invalid_provider(self):
        with assert_raises(exceptions.SubclassNotFound):
            self.sfn.provider = 'the ocean'
            self.sfn.wrapped()

    def test_get_guid_no_create(self):
        assert_is(self.sfn.get_guid(), None)

    def test_get_guid_create(self):
        guid = self.sfn.get_guid(create=True)
        assert_equal(guid.referent, self.sfn)
        assert_equal(self.sfn.get_guid(), guid)

class TestFileNodeObj(FilesTestCase):

    def test_create(self):
        with assert_raises(AssertionError):
            TestFileNode.create()

        with assert_raises(AssertionError):
            models.File.create()

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

    def test_kind(self):
        assert_equals(TestFile().kind, 'file')
        assert_equals(TestFolder().kind, 'folder')

    def test_filter_build(self):
        qs = TestFile._filter(Q('test', 'eq', 'test'))
        _, is_file, provider = qs.nodes
        assert_equal(is_file.__dict__, Q('is_file', 'eq', True).__dict__)
        assert_equal(provider.__dict__, Q('provider', 'eq', 'test').__dict__)

    def test_resolve_class(self):
        assert_equal(
            TestFile,
            models.FileNode.resolve_class('test', models.FileNode.FILE)
        )
        assert_equal(
            TestFolder,
            models.FileNode.resolve_class('test', models.FileNode.FOLDER)
        )
        assert_equal(
            TestFileNode,
            models.FileNode.resolve_class('test', models.FileNode.ANY)
        )

    def test_find(self):
        models.StoredFileNode.remove_one(self.node.get_addon('osfstorage').root_node)
        models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).save()

        models.StoredFileNode(
            path='afolder',
            name='name',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name2/',
        ).save()

        expected = ['afile', 'afolder']
        select = lambda y: [x.path for x in y.find()]

        assert_equal(expected, select(models.FileNode))
        assert_equal(expected, select(TestFileNode))
        assert_equal(['afile'], select(TestFile))
        assert_equal(['afile'], select(models.File))
        assert_equal(['afolder'], select(TestFolder))
        assert_equal(['afolder'], select(models.Folder))

    def test_find_one(self):
        models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).save()
        found = TestFile.find_one(Q('path', 'eq', 'afile'))
        assert_true(isinstance(found, TestFile))
        assert_equal(found.materialized_path, '/long/path/to/name')

    def test_load(self):
        item = models.StoredFileNode(
            path='afolder',
            name='name',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name2/',
        )
        item.save()

        assert_is(models.FileNode.load('notanid'), None)
        assert_true(isinstance(TestFolder.load(item._id), TestFolder))
        assert_true(isinstance(models.FileNode.load(item._id), TestFolder))
        with assert_raises(AssertionError):
            TestFile.load(item._id)

    def test_parent(self):
        parent = models.StoredFileNode(
            path='afolder',
            name='name',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name2/',
        ).wrapped()
        parent.save()

        child = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()
        child.save()

        assert_is(child.parent, None)
        assert_false(isinstance(parent, models.StoredFileNode))
        child.parent = parent
        assert_true(isinstance(child.parent, models.FileNode))
        child.parent = parent.stored_object
        assert_true(isinstance(child.parent, models.FileNode))

    def test_save(self):
        child = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

        assert_false(child._is_loaded)
        assert_false(child.stored_object._is_loaded)
        child.save()
        assert_true(child._is_loaded)
        assert_true(child.stored_object._is_loaded)

    def test_delete(self):
        models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped().delete()

        trashed = models.TrashedFileNode.find_one()
        assert_equal(trashed.path, 'afile')
        assert_equal(trashed.node, self.node)
        assert_equal(trashed.materialized_path, '/long/path/to/name')

    def test_delete_with_guid(self):
        fn = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()
        guid = fn.get_guid(create=True)
        fn.delete()

        trashed = models.TrashedFileNode.find_one()

        guid.reload()

        assert_equal(guid.referent, trashed)
        assert_equal(trashed.path, 'afile')
        assert_equal(trashed.node, self.node)
        assert_equal(trashed.materialized_path, '/long/path/to/name')
        assert_less((trashed.deleted_on - datetime.datetime.utcnow()).total_seconds(), 5)

    def test_delete_with_user(self):
        fn = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()
        fn.delete(user=self.user)

        trashed = models.TrashedFileNode.find_one()
        assert_equal(trashed.deleted_by, self.user)
        assert_equal(models.StoredFileNode.load(fn._id), None)

    def test_restore_file(self):
        root = models.StoredFileNode(
            path='root',
            name='rootfolder',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to',
        ).wrapped()
        root.save()

        fn = models.StoredFileNode(
            parent=root._id,
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

        before = fn.to_storage()
        trashed = fn.delete(user=self.user)

        assert_equal(
            trashed.restore().to_storage(),
            before
        )
        assert_equal(models.TrashedFileNode.load(trashed._id), None)

    def test_restore_folder(self):
        root = models.StoredFileNode(
            path='root',
            name='rootfolder',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/',
        ).wrapped()
        root.save()

        fn = models.StoredFileNode(
            parent=root._id,
            path='afolder',
            name='folder_name',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/folder_name',
        ).wrapped()

        before = fn.to_storage()
        trashed = fn.delete(user=self.user)

        assert_equal(
            trashed.restore().to_storage(),
            before
        )
        assert_equal(models.TrashedFileNode.load(trashed._id), None)

    def test_restore_folder_nested(self):
        def build_tree(acc=None, parent=None, atleastone=False):
            import random
            acc = acc or []
            if len(acc) > 50:
                return acc
            is_folder = atleastone
            for i in range(random.randrange(3, 15)):
                fn = models.StoredFileNode(
                    path='name{}'.format(i),
                    name='name{}'.format(i),
                    is_file=not is_folder,
                    node=self.node,
                    parent=parent._id,
                    provider='test',
                    materialized_path='{}/{}'.format(parent.materialized_path, 'name{}'.format(i)),
                ).wrapped()
                fn.save()
                random.randint(0, 5) == 1
                if is_folder:
                    build_tree(acc, fn)
                acc.append(fn)
                is_folder = random.randint(0, 5) == 1
            return acc

        root = models.StoredFileNode(
            path='root',
            name='rootfolder',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/',
        ).wrapped()
        root.save()

        parent = models.StoredFileNode(
            parent=root._id,
            path='afolder',
            name='folder_name',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/folder_name',
        ).wrapped()
        parent.save()

        branch = models.StoredFileNode(
            path='afolder',
            name='folder_name',
            is_file=False,
            node=self.node,
            provider='test',
            parent=parent._id,
            materialized_path='/long/path/to/folder_name',
        ).wrapped()
        branch.save()

        round1 = build_tree(parent=branch, atleastone=True)
        round2 = build_tree(parent=parent, atleastone=True)

        stay_deleted = [branch.to_storage()] + [child.to_storage() for child in round1]
        get_restored = [parent.to_storage()] + [child.to_storage() for child in round2]

        branch.delete()

        for data in stay_deleted:
            assert_true(models.TrashedFileNode.load(data['_id']))
            assert_is(models.StoredFileNode.load(data['_id']), None)

        trashed = parent.delete()

        for data in get_restored:
            assert_true(models.TrashedFileNode.load(data['_id']))
            assert_is(models.StoredFileNode.load(data['_id']), None)

        trashed.restore()

        for data in stay_deleted:
            assert_true(models.TrashedFileNode.load(data['_id']))
            assert_is(models.StoredFileNode.load(data['_id']), None)

        for data in get_restored:
            assert_is(models.TrashedFileNode.load(data['_id']), None)
            assert_equals(models.StoredFileNode.load(data['_id']).to_storage(), data)

    def test_metadata_url(self):
        pass

    def test_move_under(self):
        pass

    def test_copy_under(self):
        pass

    def test_attr_passthrough(self):
        stored = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        )
        stored.test = 'Foo'
        stored.bar = ['wat']
        wrapped = stored.wrapped()
        wrapped.bar.append('wat')

        assert_equal(stored.bar, wrapped.bar)
        assert_equal(stored.test, wrapped.test)

    def test_repr(self):
        child = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

        assert_true(isinstance(child.__repr__(), basestring))


class TestFileObj(FilesTestCase):

    def test_get_version(self):
        v1 = models.FileVersion(identifier='1')
        v2 = models.FileVersion(identifier='2')
        v1.save()
        v2.save()

        file = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

        file.versions.extend([v1, v2])

        assert_equals(file.get_version('1'), v1)
        assert_equals(file.get_version('2', required=True), v2)

        assert_is(file.get_version('3'), None)

        with assert_raises(exceptions.VersionNotFoundError):
            file.get_version('3', required=True)

    def test_update_version_metadata(self):
        v1 = models.FileVersion(identifier='1')
        v1.save()

        file = models.StoredFileNode(
            path='afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

        file.versions.append(v1)
        file.update_version_metadata(None, {'size': 1337})

        with assert_raises(exceptions.VersionNotFoundError):
            file.update_version_metadata('3', {})

        assert_equal(v1.size, 1337)

    @mock.patch('website.files.models.base.requests.get')
    def test_touch(self, mock_requests):
        file = models.StoredFileNode(
            path='/afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

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
        assert_equals(len(file.versions), 0)

    @mock.patch('website.files.models.base.requests.get')
    def test_touch_caching(self, mock_requests):
        file = models.StoredFileNode(
            path='/afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

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
        assert_equals(len(file.versions), 1)
        assert_is(file.touch(None, revision='foo'), v)

    @mock.patch('website.files.models.base.requests.get')
    def test_touch_auth(self, mock_requests):
        file = models.StoredFileNode(
            path='/afile',
            name='name',
            is_file=True,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()

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
        self.parent = models.StoredFileNode(
            path='aparent',
            name='parent',
            is_file=False,
            node=self.node,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()
        self.parent.save()

    def test_children(self):
        models.StoredFileNode(
            path='afile',
            name='child',
            is_file=True,
            node=self.node,
            parent=self.parent._id,
            provider='test',
            materialized_path='/long/path/to/name',
        ).save()

        assert_equal(len(list(self.parent.children)), 1)

        models.StoredFileNode(
            path='afile2',
            name='child2',
            is_file=True,
            node=self.node,
            parent=self.parent._id,
            provider='test',
            materialized_path='/long/path/to/name',
        ).save()

        assert_equal(len(list(self.parent.children)), 2)

    def test_delete(self):
        child = models.StoredFileNode(
            path='afile',
            name='child',
            is_file=True,
            node=self.node,
            parent=self.parent._id,
            provider='test',
            materialized_path='/long/path/to/name',
        ).wrapped()
        child.save()

        guid = self.parent.get_guid(create=True)
        child_guid = child.get_guid(create=True)

        trashed_parent = self.parent.delete(user=self.user)

        guid.reload()
        child_guid.reload()

        assert_equal(
            trashed_parent,
            models.TrashedFileNode.load(child._id).parent
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


class TestUtils(FilesTestCase):

    def test_genwrapper_repr(self):
        wrapped = models.FileNode.find()
        assert_true(isinstance(wrapped, utils.GenWrapper))
        assert_in(wrapped.mqs.__repr__(), wrapped.__repr__())

    def test_genwrapper_getattr(self):
        with assert_raises(AttributeError) as e:
            models.FileNode.find().test
        assert_equal(e.exception.message, "'GenWrapper' object has no attribute 'test'")


class TestFileVersion(FilesTestCase):
    pass


class TestSubclasses(FilesTestCase):

    @mock.patch.object(models.File, 'touch')
    def test_s3file(self, mock_touch):
        file = models.S3File.create(
            path='afile2',
            name='child2',
            is_file=True,
            node=self.node,
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
