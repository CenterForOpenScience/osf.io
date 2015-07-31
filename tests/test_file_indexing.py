import functools
import logging
import mock
import time
import unittest

from nose import tools
from nose.tools import *

from framework.auth import Auth
from tests import factories
from tests.test_archiver import use_fake_addons
from tests.test_elastic import query
from tests.factories import ModularOdmFactory
from tests.factories import ProjectWithAddonFactory
from tests.test_elastic import SearchTestCase
from tests.base import OsfTestCase
from website import settings
from website.search import elastic_search
from website.search import search
from website.search import file_util
from website.search import file_indexing
from website.addons.base import GuidFile
from website.addons.osfstorage.model import OsfStorageFileNode, OsfStorageNodeSettings

FILE_SIZE = 1000
FILE_CONTENT = 'You must talk to him; tell him that he is a good cat, and a pretty cat, and...'

class PatchedContext(object):
    """Create a context with multiple patches."""
    def __init__(self, *args, **kwargs):
        self.mocks = []
        self.named_mocks = {}
        self.patches = args
        self.named_patches = kwargs

    def __enter__(self):
        for patch in self.patches:
            self.mocks.append(patch.start())

        for name, patch in self.named_patches.iteritems():
            self.named_mocks.update({name: patch.start()})

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for patch in self.patches:
            patch.stop()

    def get_named_patch(self, name):
        return self.named_patches.get(name)

    def get_named_mock(self, name):
        return self.named_mocks.get(name)


# patch for GuidFile.enrich
def _guid_file_enrich_patch(node, should_raise=None):
    node._metadata_cache = {'size': FILE_SIZE}


# patch for file_utils.get_file_content
def _get_file_content_patch(guid_file):
    return FILE_CONTENT

mock.patch('website.search.file_indexing.update_search_files'),

PATCH_CONTEXT = PatchedContext(
    mock._patch_object(GuidFile, 'enrich', _guid_file_enrich_patch),
    mock.patch('website.search.file_util.get_file_content', _get_file_content_patch),
)

TRIGGER_CONTEXT = PatchedContext(
    update_search_file=mock.patch('website.search.file_indexing.update_search_file'),
    update_search_files=mock.patch('website.search.file_indexing.update_search_files'),
    delete_search_file=mock.patch('website.search.file_indexing.delete_search_file'),
    delete_search_files=mock.patch('website.search.file_indexing.delete_search_files'),
)

def patch_context(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with PATCH_CONTEXT:
            return func(*args, **kwargs)
    return wrapper

class OsfStorageFileNodeFactory(ModularOdmFactory):
    FACTORY_FOR = OsfStorageFileNode
    name = 'test file node'
    kind = 'file'


class FileIndexingTestCase(SearchTestCase):
    def setUp(self):
        super(FileIndexingTestCase, self).setUp()
        settings.USE_FILE_INDEXING = True
        self.project = ProjectWithAddonFactory()
        self.addon = self.project.get_addon('osfstorage')
        self.file_node = self.addon.root_node.append_file('Test_File_Node.txt', save=True)
        #OsfStorageFileNodeFactory(node_settings=self.addon)


## But who shall test the tests themselves? ##
class TestFileIndexingTestCase(FileIndexingTestCase):
    def setUp(self):
        super(TestFileIndexingTestCase, self).setUp()

    def test_name_is_correct(self):
        assert_equal(self.file_node.name, 'Test_File_Node.txt')

    def test_file_node_is_file(self):
        assert_true(self.file_node.is_file)

    def test_file_nodes_settings_are_addon(self):
        assert_equal(self.file_node.node_settings, self.addon)

    def test_addon_is_osfstorage(self):
        assert_equal(self.addon.config.short_name, 'osfstorage')

    def test_projet_owns_addon(self):
        assert_equal(self.addon.owner, self.project)

    def test_project_returns_addon(self):
        assert_is(self.addon, self.project.get_addon('osfstorage'))

    def test_addons_root_has_child(self):
        assert_equal(len(self.addon.root_node.children), 1)

    def test_trigger_context_get_named_patch(self):
        with TRIGGER_CONTEXT as tcontext:
            assert_is_not_none(tcontext.get_named_patch('update_search_file'))
            assert_is_not_none(tcontext.get_named_patch('delete_search_files'))
            assert_is_none(tcontext.get_named_patch('the_meaning_of_life_the_universe_and_everything'))
            assert_is_none(tcontext.get_named_patch('file_indexing.update_search_file'))

    def test_trigger_context_get_named_mock(self):
        with TRIGGER_CONTEXT as tcontext:
            assert_is_not_none(tcontext.get_named_mock('update_search_file'))
            assert_is_not_none(tcontext.get_named_mock('delete_search_files'))
            assert_is_none(tcontext.get_named_mock('the_meaning_of_life_the_universe_and_everything'))
            assert_is_none(tcontext.get_named_mock('file_indexing.update_search_file'))

    def test_trigger_context_called_for_function(self):
        with TRIGGER_CONTEXT as tcontext:
            patch = tcontext.get_named_mock('delete_search_file')
            file_indexing.delete_search_file(self.file_node)
            patch.assert_called_once_with(self.file_node)


## file_util.py ##


class TestBuildFileDocument(FileIndexingTestCase):
    def setUp(self):
        super(TestBuildFileDocument, self).setUp()

    def test_build_file_document_with_no_content(self):
        with PATCH_CONTEXT:
            file_doc = file_util.build_file_document(self.file_node, include_content=False)
            assert_in('size', file_doc.keys())
            assert_in('content', file_doc.keys())
            assert_is(file_doc['content'], None)

    def test_build_file_document_with_content(self):
        with PATCH_CONTEXT:
            file_doc = file_util.build_file_document(self.file_node, include_content=True)
            assert_in('size', file_doc.keys())
            assert_in('content', file_doc.keys())
            assert_is_not(file_doc['content'], None)


class TestNormPath(OsfTestCase):
    def test_path_with_slash(self):
        path = '/123ab345cd'
        normed_path = file_util.norm_path(path)
        assert_equal(path[1:], normed_path)

    def test_path_with_no_slash(self):
        path = '123ab345cd'
        normed_path = file_util.norm_path(path)
        assert_equal(path, normed_path)


class TestIsIndexed(FileIndexingTestCase):
    def setUp(self):
        super(TestIsIndexed, self).setUp()
        self.indexed = [OsfStorageFileNodeFactory(node_settings=self.addon, name='test_file{}'.format(ext))
                        for ext in file_util.INDEXED_TYPES]
        self.not_indexed = [OsfStorageFileNodeFactory(node_settings=self.addon, name='test_file.png')]

    def test_true_for_indexed_types(self):
        for file_node in self.indexed:
            assert_true(file_util.is_indexed(file_node), '{} was indexed'.format(repr(file_node)))

    def test_false_for_not_indexed_types(self):
        for file_node in self.not_indexed:
            assert_false(file_util.is_indexed(file_node), '{} was not indexed'.format(repr(file_node)))


class TestCollectFiles(FileIndexingTestCase):
    def setUp(self):
        super(TestCollectFiles, self).setUp()
        fnode_one = self.addon.root_node.append_file(factories.fake.file_name(), save=True)
        fnode_two = self.addon.root_node.append_file(factories.fake.file_name(), save=True)
        folder_node = self.addon.root_node.append_folder('folder one', save=True)
        fnode_three = folder_node.append_file(factories.fake.file_name(), save=True)
        fnode_four = folder_node.append_file(factories.fake.file_name(), save=True)

    def test_addon_has_four_children(self):
        count = len(self.addon.root_node.children)
        assert_equal(count, 4)

    def test_collect_files_gives_correct_number_of_files(self):
        file_util.collect_files(self.project)
        count = len([f for f in file_util.collect_files(self.addon.owner)])
        assert_equal(count, 5)

    def test_from_filenode_gives_correct_number_of_files(self):
        count = len([f for f in file_util.collect_files_from_filenode(self.addon.root_node)])
        assert_equal(count, 5)


#TODO: Test file_util.get_file_content
class TestGetFileContent(FileIndexingTestCase):
    pass


## elastic_search.py / search.py ##


def query(text, index=None):
    index = index or settings.ELASTIC_INDEX
    body = {'query': {'query_string': {'query': text}}}
    resp = elastic_search.es.search(body=body, index=index)
    hits = resp['hits']['hits']
    return hits


class TestSearchFileFunctions(FileIndexingTestCase):
    def setUp(self):
        super(TestSearchFileFunctions, self).setUp()
        root = self.addon.root_node
        root.append_file(factories.fake.file_name(extension='txt'))
        folder = root.append_folder(factories.fake.first_name())
        folder.append_file(factories.fake.file_name(extension='txt'))

    @patch_context
    def test_update_delete_single_file(self):
        assert_equal(len(query('cat')), 0)

        search.update_file(self.file_node, settings.ELASTIC_INDEX)

        time.sleep(1)
        assert_equal(len(query('cat')), 1, 'failed to update')

        search.delete_file(self.file_node, settings.ELASTIC_INDEX)

        time.sleep(1)
        assert_equal(len(query('cat')), 0, 'failed to delete')

    @patch_context
    def test_update_delete_all_files(self):
        assert_equal(len(query('cat')), 0)

        search.update_all_files(self.project, settings.ELASTIC_INDEX)

        time.sleep(1)
        assert_equal(len(query('cat')), 3, 'failed to update')

        search.delete_all_files(self.project, settings.ELASTIC_INDEX)

        time.sleep(1)
        assert_equal(len(query('cat')), 0, 'failed to delete')

