import factories
import mock

from nose.tools import *  # flake8: noqa (PEP8 asserts)

from tests.base import OsfTestCase
from website.search.index_file import collect_files

FILE_TREE = {
    'name': 'fake_file_tree',
    'children': [],
}

DOWNLOAD_HANDLERS = {}

# fakes

class FakeResponse():
    def __init__(self, content):
        self.content = content

    @property
    def text(self):
        return self.content


def fake_request_get(*args, **kwargs):
    url = args[0]
    path_start = url.rfind('/')
    argument_start = url.find('&') if url.find('&') > 0 else None
    path = url[path_start:argument_start] if argument_start else url[path_start:]
    if url[:11] == 'http://fake':
        for file_path, contents in DOWNLOAD_HANDLERS.iteritems():
            if path == file_path:
                return FakeResponse(contents)
    raise ValueError('{} not mocked'.format(url))


@property
def fake_download_url(*args, **kwargs):
    path = args[0].path
    return 'http://fake{}'.format(path)


def fake_file_tree(*args, **kwargs):
    return FILE_TREE

# global file functions

def add_file(name, path, contents):
    global FILE_TREE
    global DOWNLOAD_HANDLERS
    FILE_TREE['children'].append({'type': 'file', 'name': name, 'path': path})
    DOWNLOAD_HANDLERS[path] = contents


def add_folder(name):
    global FILE_TREE
    FILE_TREE['children'].append({
        'type': 'folder',
        'name': name,
        'children': [],
    })


def add_file_to_folder(folder_name, file_name, path, contents):
    global FILE_TREE
    global DOWNLOAD_HANDLERS

    for child in FILE_TREE['children']:
        if child['type'] == 'folder':
            if child['name'] == folder_name:
                child['children'].append({
                    'type': 'file',
                    'name': file_name,
                    'path': path
                })
                DOWNLOAD_HANDLERS[path] = contents
                return
    raise ValueError('Folder {} does not exist'.format(folder_name))

def reset_files():
    global FILE_TREE
    global DOWNLOAD_HANDLERS

    FILE_TREE['children'] = []
    DOWNLOAD_HANDLERS = {}

# Tests

class TestCollectFiles(OsfTestCase):
    def setUp(self):
        self._start_mocks()
        self.fake_project_with_addon = factories.ProjectWithAddonFactory()
        self.fake_project_with_addon.add_addon('github', None)
        self.fake_project_with_addon.add_addon('brandons_addon', None)

    def tearDown(self):
        self._stop_mocks()
        reset_files()

    def _start_mocks(self):
        self.file_tree_patch = mock.patch('website.addons.base.StorageAddonBase._get_file_tree', fake_file_tree)
        self.download_url_patch = mock.patch('website.addons.base.GuidFile.download_url', fake_download_url)
        self.request_patch = mock.patch('website.search.index_file.requests.get', fake_request_get)

        self.file_tree_patch.start()
        self.download_url_patch.start()
        self.request_patch.start()

    def _stop_mocks(self):
        self.file_tree_patch.stop()
        self.download_url_patch.stop()
        self.request_patch.stop()

    def test_collect_single_file(self):
        add_file('file_one.txt', '/file_one', 'This is file one.')
        for file_ in collect_files(self.fake_project_with_addon):
            assert_equal(file_['name'], 'file_one.txt')
            assert_equal(file_['content'], 'This is file one.')

    def test_collect_multiple_files(self):
        add_file('file_one.txt', '/file_one', 'This is file one.')
        add_file('file_two.txt', '/file_two', 'This is file two.')
        for i, file_ in enumerate(collect_files(self.fake_project_with_addon)):
            if i == 0:
                assert_equal(file_['name'], 'file_one.txt')
                assert_equal(file_['content'], 'This is file one.')
            if i == 1:
                assert_equal(file_['name'], 'file_two.txt')
                assert_equal(file_['content'], 'This is file two.')

    def test_collect_with_folder(self):
        add_folder('folder')
        add_file_to_folder('folder', 'file_one.txt', '/file_one', 'This is file one.')
        for file_ in collect_files(self.fake_project_with_addon):
            assert_equal(file_['name'], 'file_one.txt', 'This is file one.')
            assert_equal(file_['content'], 'This is file one.')
