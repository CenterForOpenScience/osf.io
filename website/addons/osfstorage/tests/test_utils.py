# -*- coding: utf-8 -*-

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage.tests import factories

from website.addons.osfstorage import model
from website.addons.osfstorage import utils


class TestHGridUtils(OsfTestCase):

    def setUp(self):
        super(TestHGridUtils, self).setUp()
        self.project = ProjectFactory()

    def test_build_urls_folder(self):
        file_tree = model.FileTree(
            path='god/save/the/queen',
            node_settings=self.project.get_addon('osfstorage'),
        )
        expected = {
            'upload': '/api/v1/project/{0}/osfstorage/files/{1}/'.format(
                self.project._id,
                file_tree.path,
            ),
            'fetch': '/api/v1/project/{0}/osfstorage/files/{1}/'.format(
                self.project._id,
                file_tree.path,
            ),
        }
        urls = utils.build_hgrid_urls(file_tree, self.project)
        assert_equal(urls, expected)


    def test_build_urls_file(self):
        file_record = model.FileRecord(
            path='kind/of/magic.mp3',
            node_settings=self.project.get_addon('osfstorage'),
        )
        expected = {
            'view': '/project/{0}/osfstorage/files/{1}/'.format(
                self.project._id,
                file_record.path,
            ),
            'download': '/project/{0}/osfstorage/files/{1}/download/'.format(
                self.project._id,
                file_record.path,
            ),
            'delete': '/api/v1/project/{0}/osfstorage/files/{1}/'.format(
                self.project._id,
                file_record.path,
            ),
        }
        urls = utils.build_hgrid_urls(file_record, self.project)
        assert_equal(urls, expected)

    def test_serialize_metadata_folder(self):
        file_tree = model.FileTree(
            path='god/save/the/queen',
            node_settings=self.project.get_addon('osfstorage'),
        )
        permissions = {'edit': False, 'view': True}
        serialized = utils.serialize_metadata_hgrid(
            file_tree,
            self.project,
            permissions,
        )
        assert_equal(serialized['addon'], 'osfstorage')
        assert_equal(serialized['path'], 'god/save/the/queen')
        assert_equal(serialized['name'], 'queen')
        assert_equal(serialized['ext'], '')
        assert_equal(serialized['kind'], 'folder')
        assert_equal(
            serialized['urls'],
            utils.build_hgrid_urls(file_tree, self.project),
        )
        assert_equal(serialized['permissions'], permissions)

    def test_serialize_metadata_file(self):
        file_record = model.FileRecord(
            path='kind/of/magic.mp3',
            node_settings=self.project.get_addon('osfstorage'),
        )
        permissions = {'edit': False, 'view': True}
        serialized = utils.serialize_metadata_hgrid(
            file_record,
            self.project,
            permissions,
        )
        assert_equal(serialized['addon'], 'osfstorage')
        assert_equal(serialized['path'], 'kind/of/magic.mp3')
        assert_equal(serialized['name'], 'magic.mp3')
        assert_equal(serialized['ext'], '.mp3')
        assert_equal(serialized['kind'], 'item')
        assert_equal(
            serialized['urls'],
            utils.build_hgrid_urls(file_record, self.project),
        )
        assert_equal(serialized['permissions'], permissions)

    def test_get_item_kind_folder(self):
        assert_equal(
            utils.get_item_kind(model.FileTree()),
            'folder',
        )

    def test_get_item_kind_file(self):
        assert_equal(
            utils.get_item_kind(model.FileRecord()),
            'item',
        )

    def test_get_item_kind_invalid(self):
        with assert_raises(TypeError):
            utils.get_item_kind('pizza')

