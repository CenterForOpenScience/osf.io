import unittest
import factories
import mock

from nose.tools import *  # flake8: noqa (PEP8 asserts)

from tests.base import OsfTestCase
from website.search.index_file import collect_files

# fakes

class FakeResponse():
    def __init__(self, content):
        self.content = content

    @property
    def text(self):
        return self.content


@property
def fake_download_url(*args, **kwargs):
    path = args[0].path
    return 'http://fake{}'.format(path)

# Tests

class FileTreeTestCase(unittest.TestCase):
    def setUp(self):
        super(FileTreeTestCase, self).setUp()
        self.FILE_TREE = {
            'name': 'fake_file_tree',
            'children': [],
        }
        self.DOWNLOAD_HANDLERS = {}

    def get_fake_file_tree(self, *args, **kwargs):
        return self.FILE_TREE

    def make_fake_request_get(self, *args, **kwargs):
        url = args[0]
        path_start = url.rfind('/')
        argument_start = url.find('&') if url.find('&') > 0 else None
        path = url[path_start:argument_start] if argument_start else url[path_start:]
        if url[:11] == 'http://fake':
            for file_path, contents in self.DOWNLOAD_HANDLERS.iteritems():
                if path == file_path:
                    return FakeResponse(contents)
        raise ValueError('{} not mocked'.format(url))

    def tearDown(self):
        super(FileTreeTestCase, self).tearDown()
        self.reset_files()

    def add_file(self, name, path, contents):
        self.FILE_TREE['children'].append({'type': 'file', 'name': name, 'path': path})
        self.DOWNLOAD_HANDLERS[path] = contents

    def add_folder(self, name):
        self.FILE_TREE['children'].append({
            'type': 'folder',
            'name': name,
            'children': [],
        })

    def add_file_to_folder(self, folder_name, file_name, path, contents):
        for child in self.FILE_TREE['children']:
            if child['type'] == 'folder':
                if child['name'] == folder_name:
                    child['children'].append({
                        'type': 'file',
                        'name': file_name,
                        'path': path
                    })
                    self.DOWNLOAD_HANDLERS[path] = contents
                    return
        raise ValueError('Folder {} does not exist'.format(folder_name))

    def reset_files(self):
        self.FILE_TREE['children'] = []
        self.DOWNLOAD_HANDLERS = {}


class TestCollectFiles(OsfTestCase, FileTreeTestCase):
    def setUp(self):
        super(TestCollectFiles, self).setUp()
        self._start_mocks()
        self.fake_project_with_addon = factories.ProjectWithAddonFactory()
        self.fake_project_with_addon.add_addon('github', None)

    def tearDown(self):
        super(TestCollectFiles, self).tearDown()
        self._stop_mocks()

    def _start_mocks(self):
        self.file_tree_patch = mock.patch('website.addons.base.StorageAddonBase._get_file_tree', self.get_fake_file_tree)
        self.download_url_patch = mock.patch('website.addons.base.GuidFile.download_url', fake_download_url)
        self.request_patch = mock.patch('website.search.index_file.requests.get', self.make_fake_request_get)

        self.file_tree_patch.start()
        self.download_url_patch.start()
        self.request_patch.start()

    def _stop_mocks(self):
        self.file_tree_patch.stop()
        self.download_url_patch.stop()
        self.request_patch.stop()

    def test_collect_single_file(self):
        self.add_file('file_one.txt', '/file_one', 'This is file one.')
        for file_ in collect_files(self.fake_project_with_addon):
            assert_equal(file_['name'], 'file_one.txt')
            assert_equal(file_['content'], 'This is file one.')

    def test_collect_multiple_files(self):
        self.add_file('file_one.txt', '/file_one', 'This is file one.')
        self.add_file('file_two.txt', '/file_two', 'This is file two.')
        for i, file_ in enumerate(collect_files(self.fake_project_with_addon)):
            if i == 0:
                assert_equal(file_['name'], 'file_one.txt')
                assert_equal(file_['content'], 'This is file one.')
            if i == 1:
                assert_equal(file_['name'], 'file_two.txt')
                assert_equal(file_['content'], 'This is file two.')

    def test_collect_with_folder(self):
        self.add_folder('folder')
        self.add_file_to_folder('folder', 'file_one.txt', '/file_one', 'This is file one.')
        for file_ in collect_files(self.fake_project_with_addon):
            assert_equal(file_['name'], 'file_one.txt', 'This is file one.')
            assert_equal(file_['content'], 'This is file one.')

    def test_does_not_include_images(self):
        self.add_file('file_one.txt', '/f_one', 'No one expects the finches swim audition!')
        self.add_file('file_two.png', '/f_two', '*A picture of the moon*')
        self.add_file('file_two.jpg', '/f_two', '*A picture of the moon*')
        self.add_file('file_two.jpeg', '/f_two', '*A picture of the moon*')
        self.add_file('file_two.bmp', '/f_two', '*A picture of the moon*')
        for file_ in collect_files(self.fake_project_with_addon):
            assert_equal(file_['name'], 'file_one.txt')
