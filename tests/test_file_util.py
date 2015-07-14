import unittest
import factories
import mock

from nose.tools import *  # flake8: noqa (PEP8 asserts)

from tests.base import OsfTestCase
from website.search.file_util import collect_files


FILE_CONTENTS = 'The contents of a file.'


class IndexFileTestCase(unittest.TestCase):
    def setUp(self):
        super(IndexFileTestCase, self).setUp()
        self.FILE_TREE = {
            'name': 'fake_file_tree',
            'children': [],
        }
        self.DOWNLOAD_HANDLERS = {}
        self._start_mocks()

    def tearDown(self):
        super(IndexFileTestCase, self).tearDown()
        self._reset_files()
        self._stop_mocks()

    def get_fake_file_tree(self, *args, **kwargs):
        return self.FILE_TREE

    def _add_file(self, name, path):
        self.FILE_TREE['children'].append({'type': 'file',
                                           'name': name,
                                           'path': path,
                                           })

    def _reset_files(self):
        self.FILE_TREE['children'] = []
        self.DOWNLOAD_HANDLERS = {}

    def _start_mocks(self):
        self.file_tree_patch = mock.patch('website.addons.base.StorageAddonBase._get_file_tree',
                                          self.get_fake_file_tree)
        self.file_tree_patch.start()

    def _stop_mocks(self):
        self.file_tree_patch.stop()


class TestCollectFiles(OsfTestCase, IndexFileTestCase):
    def setUp(self):
        super(TestCollectFiles, self).setUp()
        self.fake_project_with_addon = factories.ProjectWithAddonFactory()

    def test_collect_no_filed(self):
        for file_ in collect_files(self.fake_project_with_addon):
            assert_true(False)
        assert_true(True)

    def test_collect_single_file(self):
        self._add_file('file_one.txt', '/file_one')
        for file_ in collect_files(self.fake_project_with_addon):
            assert_equal(file_['name'], 'file_one.txt')
            assert_equal(file_['path'], '/file_one')

    def test_collect_multiple_files(self):
        self._add_file('file_one.txt', '/file_one')
        self._add_file('file_two.txt', '/file_two')
        for i, file_ in enumerate(collect_files(self.fake_project_with_addon)):
            if i == 0:
                assert_equal(file_['name'], 'file_one.txt')
            if i == 1:
                assert_equal(file_['name'], 'file_two.txt')

    def test_collect_nested_files(self):
        self._add_file('file_one.txt', '/file_one')
        self._add_file('file_two.txt', '/file_two')
        self.FILE_TREE['children'].append({
            'name': 'sub_tree',
            'children': self.FILE_TREE['children'][:]
        })
        self.FILE_TREE['children']
        for i, file_ in enumerate(collect_files(self.fake_project_with_addon)):
            if i % 2 == 0:
                assert_equal(file_['name'], 'file_one.txt')
            if i % 2 == 1:
                assert_equal(file_['name'], 'file_two.txt')

    def test_does_not_include_images(self):
        self._add_file('file_one.txt', '/f_one')
        self._add_file('file_two.png', '/f_two')
        self._add_file('file_three.jpeg', '/f_three')
        self._add_file('file_four.bmp', '/f_four')
        for file_ in collect_files(self.fake_project_with_addon):
            assert_equal(file_['name'], 'file_one.txt')
