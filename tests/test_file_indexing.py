import functools
import mock
import os
import time
import unittest

from nose.tools import *

from tests import factories
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
from website.addons.osfstorage.model import OsfStorageFileNode

FILE_SIZE = 1000
FILE_CONTENT = 'You must talk to him; tell him that he is a good cat, and a pretty cat, and...'


class PatchedContext(object):
    """ Create a context with multiple patches.

    some_useful_patches = PatchContext(
        method_one = mock.patch('some.far.away.method_one'),
        method_two = mock.patch('some.other.method'),
    )

    with some_useful_patches as patches:
        run_tests()
        patches.get('method_one').assert_called_once_with('something')

    """
    def __init__(self, *args, **kwargs):
        self.mocks = []
        self.named_mocks = {}
        self.patches = args
        self.named_patches = kwargs

    def __enter__(self):
        for patch in self.patches:
            self.mocks.append(patch.start())

        for name, patch in self.named_patches.iteritems():
            patch_mock = patch.start()
            self.named_mocks.update({name: patch_mock})
            self.mocks.append(patch_mock)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for patch in self.patches:
            patch.stop()

        for patch in self.named_patches.values():
            patch.stop()

    def get_named_patch(self, name):
        return self.named_patches.get(name)

    def get_named_mock(self, name):
        return self.named_mocks.get(name)


# patch for GuidFile.enrich
def _guid_file_enrich_patch(node, should_raise=None):
    node._metadata_cache = {'size': FILE_SIZE}


# patch for file_utils.get_file_content
def _get_file_content_patch(guid_file, include_content=None):
    return FILE_CONTENT


def _load_local_file_content_patch(file_node, include_content=None):
    cur_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(cur_path, 'test_files', file_node.name)
    with open(file_path, 'rb') as f:
        content = f.read()
    return content


PATCH_CONTEXT = PatchedContext(
    mock.patch.object(GuidFile, 'enrich', _guid_file_enrich_patch),
    mock.patch('website.search.file_util.get_file_content', _get_file_content_patch),
)

TRIGGER_CONTEXT = PatchedContext(
    update_search_file=mock.patch('website.search.file_indexing.update_search_file'),
    update_search_files=mock.patch('website.search.file_indexing.update_search_files'),
    delete_search_file=mock.patch('website.search.file_indexing.delete_search_file'),
    delete_search_files=mock.patch('website.search.file_indexing.delete_search_files'),
    move_search_file=mock.patch('website.search.file_indexing.move_search_file'),
    copy_search_file=mock.patch('website.search.file_indexing.copy_search_file'),
)

LOAD_LOCAL_FILE_CONTEXT = PatchedContext(
    mock.patch('website.search.file_util.get_file_content', _load_local_file_content_patch)
)


def patch_context(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with PATCH_CONTEXT:
            return func(*args, **kwargs)
    return wrapper


def query(text, index=None):
    index = index or settings.ELASTIC_INDEX
    body = {'query': {'query_string': {'query': text}}}
    resp = elastic_search.es.search(body=body, index=index)
    hits = resp['hits']['hits']
    return hits


def file_count(parent_doctype, index=None):
    index = index or settings.ELASTIC_INDEX
    body = {'query': {'query_string': {'query': '*'}}}
    resp = elastic_search.es.search(doc_type='{}_file'.format(parent_doctype), body=body, index=index)
    count = len(resp['hits']['hits'])
    return count


def get_file(file_id, file_parent, index=None):
    resp = elastic_search.es.get(
        index=index or settings.ELASTIC_INDEX,
        doc_type='file',
        id=file_id,
        parent=file_parent,
        ignore=404,
    )
    return resp['found']

class OsfStorageFileNodeFactory(ModularOdmFactory):
    FACTORY_FOR = OsfStorageFileNode
    name = 'test file node'
    kind = 'file'
    node_settings = None


class FileIndexingTestCase(SearchTestCase):
    def setUp(self):
        super(FileIndexingTestCase, self).setUp()
        with PATCH_CONTEXT:
            settings.USE_FILE_INDEXING = True
            self.project = ProjectWithAddonFactory()
            self.project.is_public = True
            self.addon = self.project.get_addon('osfstorage')
            self.file_node = self.addon.root_node.append_file('Test_File_Node.txt', save=True)


# But who shall test the tests themselves?
class TestFileIndexingTestCase(FileIndexingTestCase):
    def setUp(self):
        super(TestFileIndexingTestCase, self).setUp()
        settings.USE_FILE_INDEXING = True

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

    def test_file_count(self):
        elastic_search.es.index(
            doc_type='project_file',
            body={'name': 'test'},
            parent='12345',
            index=settings.ELASTIC_INDEX,
        )
        elastic_search.es.index(
            doc_type='project_file',
            body={'name': 'test_two'},
            parent='67890',
            index=settings.ELASTIC_INDEX,
        )
        time.sleep(1)
        count = file_count(parent_doctype='project')
        assert_equal(2, count)

    def test_get_existing_file(self):
        elastic_search.es.index(
            doc_type='file',
            body={'name': 'test'},
            parent='12345',
            index=settings.ELASTIC_INDEX,
            id='abcde'
        )
        time.sleep(1)
        assert_true(get_file('abcde', '12345', settings.ELASTIC_INDEX))

    def test_get_non_existing_file(self):
        assert_false(get_file('abcde', '12345', settings.ELASTIC_INDEX))


# file_util.py


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
            assert_true(file_util.is_indexed(file_node=file_node), '{} was indexed'.format(repr(file_node)))

    def test_false_for_not_indexed_types(self):
        for file_node in self.not_indexed:
            assert_false(file_util.is_indexed(file_node=file_node), '{} was not indexed'.format(repr(file_node)))


class TestCollectFiles(FileIndexingTestCase):
    def setUp(self):
        super(TestCollectFiles, self).setUp()
        with PATCH_CONTEXT:
            self.addon.root_node.append_file(factories.fake.file_name(), save=True)
            self.addon.root_node.append_file(factories.fake.file_name(), save=True)
            folder = self.addon.root_node.append_folder('folder one', save=True)
            folder.append_file(factories.fake.file_name(), save=True)
            folder.append_file(factories.fake.file_name(), save=True)

    def test_addon_has_correct_number_of_children(self):
        count = len(self.addon.root_node.children)
        assert_equal(count, 4)

    def test_collect_files_gives_correct_number_of_files(self):
        file_util.collect_files(self.project)
        count = len([f for f in file_util.collect_files(self.addon.owner)])
        assert_equal(count, 5)

    def test_from_filenode_gives_correct_number_of_files(self):
        count = len([f for f in file_util.collect_files_from_filenode(self.addon.root_node)])
        assert_equal(count, 5)

    def test_collects_from_component(self):
        component = ProjectWithAddonFactory(parent=self.project)
        addon = component.get_addon('osfstorage')
        with PATCH_CONTEXT:
            component.is_public = True
            addon.root_node.append_file(factories.fake.file_name(), save=True)
            addon.root_node.append_file(factories.fake.file_name(), save=True)
            addon.root_node.append_file(factories.fake.file_name(), save=True)

            self.addon.root_node.append_file(factories.fake.file_name(), save=True)
            folder_two = self.addon.root_node.append_folder('folder two')
            folder_two.node_settings.root_node.append_file(factories.fake.file_name())
        count = len([f for f in file_util.collect_files(self.addon.owner)])
        assert_equal(count, 10)

    def test_no_collection_from_private_component(self):
        component = ProjectWithAddonFactory(parent=self.project)
        addon = component.get_addon('osfstorage')

        with PATCH_CONTEXT:
            addon.root_node.append_file(factories.fake.file_name(), save=True)
            addon.root_node.append_file(factories.fake.file_name(), save=True)
            addon.root_node.append_file(factories.fake.file_name(), save=True)

        count = len([f for f in file_util.collect_files(self.addon.owner)])
        assert_equal(count, 5)


# TODO: Test file_util.get_file_content
class TestGetFileContent(FileIndexingTestCase):
    pass

class TestGetFileSize(FileIndexingTestCase):
    pass

class TestGetFileContentUrl(FileIndexingTestCase):
    pass


# elastic_search.py / search.py


class TestIndexRealFiles(FileIndexingTestCase):
    def setUp(self):
        super(TestIndexRealFiles, self).setUp()
        self.root = self.addon.root_node
        self.mock_size = mock.patch('website.search.file_util.get_file_size', return_value=10)
        self.mock_size.start()

    def tearDown(self):
        super(TestIndexRealFiles, self).tearDown()
        self.mock_size.stop()

    @patch_context
    def test_txt_file_searchable(self):
        self.file_node_txt = self.root.append_file('index_test.txt')
        with LOAD_LOCAL_FILE_CONTEXT:
            assert_equal(len(query('diamond')), 0)
            search.update_file(self.file_node_txt, settings.ELASTIC_INDEX)
            time.sleep(1)
            assert_equal(len(query('diamond')), 1)

    @patch_context
    def test_rtf_file_searchable(self):
        self.file_node_rtf = self.root.append_file('index_test.rtf')
        with LOAD_LOCAL_FILE_CONTEXT:
            assert_equal(len(query('diamond')), 0)
            search.update_file(self.file_node_rtf, settings.ELASTIC_INDEX)
            time.sleep(1)
            assert_equal(len(query('diamond')), 1)

    @patch_context
    def test_pdf_file_searchable(self):
        self.file_node_pdf = self.root.append_file('index_test.pdf')
        with LOAD_LOCAL_FILE_CONTEXT:
            assert_equal(len(query('diamond')), 0)
            search.update_file(self.file_node_pdf, settings.ELASTIC_INDEX)
            time.sleep(1)
            assert_equal(len(query('diamond')), 1)

    @patch_context
    def test_docx_file_searchable(self):
        self.file_node_docx = self.root.append_file('index_test.docx')
        with LOAD_LOCAL_FILE_CONTEXT:
            assert_equal(len(query('diamond')), 0)
            search.update_file(self.file_node_docx, settings.ELASTIC_INDEX)
            time.sleep(1)
            assert_equal(len(query('diamond')), 1)


class TestFileNodeUpdateSearch(FileIndexingTestCase):
    def test_update_on_delete(self):
        with TRIGGER_CONTEXT as patches:
            update_search_mock = patches.get_named_mock('update_search_file')
            delete_search_mock = patches.get_named_mock('delete_search_file')
            assert_false(delete_search_mock.called)
            assert_false(update_search_mock.called)

            self.file_node.delete()

            delete_search_mock.assert_called_once_with(self.file_node)
            assert_false(update_search_mock.called)


class TestProjectPrivacyUpdatesSearch(FileIndexingTestCase):
    def test_update_on_make_public(self):
        self.project.set_privacy('private')
        with TRIGGER_CONTEXT as patches:

            self.project.set_privacy('public')
            update_all_mock = patches.get_named_mock('update_search_files')
            delete_all_mock = patches.get_named_mock('delete_search_files')
            assert_true(update_all_mock.called)
            assert_false(delete_all_mock.called)

    def test_delete_on_make_private(self):
        self.project.set_privacy('public')
        with TRIGGER_CONTEXT as patches:
            update_all_mock = patches.get_named_mock('update_search_files')
            delete_all_mock = patches.get_named_mock('delete_search_files')

            self.project.set_privacy('private')

            assert_true(delete_all_mock.called)
            assert_false(update_all_mock.called)


class TestMoveFiles(FileIndexingTestCase):
    def test_move_file(self):
        fid = '12345'
        parent_id = 'abcde'
        new_parent_id = 'fghij'
        elastic_search.es.index(
            index=settings.ELASTIC_INDEX,
            doc_type='file',
            id=fid,
            parent=parent_id,
            body={'name': 'hank_smithington.txt'},
        )
        time.sleep(1)
        assert_true(get_file(file_id=fid, file_parent=parent_id, index=settings.ELASTIC_INDEX))

        search.move_file(file_node_id=fid, old_parent_id=parent_id, new_parent_id=new_parent_id, index=settings.ELASTIC_INDEX)
        time.sleep(1)
        assert_true(get_file(file_id=fid, file_parent=new_parent_id, index=settings.ELASTIC_INDEX))

