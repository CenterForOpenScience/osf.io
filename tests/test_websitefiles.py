from nose.tools import *  # noqa
from modularodm import Q
from website.files import models

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

    def test_wrapped(self):
        assert_true(isinstance(self.sfn.wrapped(), TestFile))

    def test_get_guid_no_create(self):
        assert_is(self.sfn.get_guid(), None)

    def test_get_guid_create(self):
        guid = self.sfn.get_guid(create=True)
        assert_equal(guid.referent, self.sfn)
        assert_equal(self.sfn.get_guid(), guid)

class TestFileNodeObj(FilesTestCase):

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

    def test_metadata_url(self):
        pass

    def test_move_under(self):
        pass

    def test_copy_under(self):
        pass

    def test_attr_passthrough(self):
        pass

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
        pass

    def test_update_version_metadata(self):
        pass

    def test_touch(self):
        pass

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

        pass

    def test_append_file(self):
        self.parent.append_file('Name')
        (child, ) = list(self.parent.children)

    def test_append_folder(self):
        pass

    def test_find_child_by_name(self):
        pass


class TestFileVersion(FilesTestCase):
    pass
