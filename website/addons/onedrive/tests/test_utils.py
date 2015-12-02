# -*- coding: utf-8 -*-
"""Tests for website.addons.onedrive.utils."""
import os

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from website.project.model import NodeLog

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.onedrive.tests.utils import OneDriveAddonTestCase
from website.addons.onedrive import utils
from website.addons.onedrive.views.config import serialize_folder


class TestNodeLogger(OneDriveAddonTestCase):

    def test_log_file_added(self):
        logger = utils.OneDriveNodeLogger(
            node=self.project,
            auth=Auth(self.user),
        )
        logger.log(NodeLog.FILE_ADDED, save=True)

        last_log = self.project.logs[-1]

        assert_equal(last_log.action, "onedrive_{0}".format(NodeLog.FILE_ADDED))

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/1557
    def test_log_deauthorized_when_node_settings_are_deleted(self):
        project = ProjectFactory()
        project.add_addon('onedrive', auth=Auth(project.creator))
        dbox_settings = project.get_addon('onedrive')
        dbox_settings.delete(save=True)
        # sanity check
        assert_true(dbox_settings.deleted)

        logger = utils.OneDriveNodeLogger(node=project, auth=Auth(self.user))
        logger.log(action='node_deauthorized', save=True)

        last_log = project.logs[-1]
        assert_equal(last_log.action, 'onedrive_node_deauthorized')


def test_get_file_name():
    assert_equal(utils.get_file_name('foo/bar/baz.txt'), 'baz.txt')
    assert_equal(utils.get_file_name('/foo/bar/baz.txt'), 'baz.txt')
    assert_equal(utils.get_file_name('/foo/bar/baz.txt/'), 'baz.txt')


def test_is_subdir():
    assert_true(utils.is_subdir('foo/bar', 'foo'))
    assert_true(utils.is_subdir('foo', 'foo'))
    assert_true(utils.is_subdir('foo/bar baz', 'foo'))
    assert_true(utils.is_subdir('bar baz/foo', 'bar baz'))
    assert_true(utils.is_subdir('foo', '/'))
    assert_true(utils.is_subdir('/', '/'))

    assert_false(utils.is_subdir('foo/bar', 'baz'))
    assert_false(utils.is_subdir('foo/bar', 'bar'))
    assert_false(utils.is_subdir('foo', 'foo/bar'))
    assert_false(utils.is_subdir('', 'foo'))
    assert_false(utils.is_subdir('foo', ''))
    assert_false(utils.is_subdir('foo', None))
    assert_false(utils.is_subdir(None, 'foo'))
    assert_false(utils.is_subdir(None, None))
    assert_false(utils.is_subdir('', ''))

    assert_true(utils.is_subdir('foo/bar', 'Foo/bar'))
    assert_true(utils.is_subdir('Foo/bar', 'foo/bar'))


def test_clean_path():
    assert_equal(utils.clean_path('/'), '/')
    assert_equal(utils.clean_path('/foo/bar/baz/'), 'foo/bar/baz')
    assert_equal(utils.clean_path(None), '')


def test_get_share_folder_uri():
    expected = 'https://onedrive.com/home/foo?shareoptions=1&share_subfolder=0&share=1'
    assert_equal(utils.get_share_folder_uri('/foo/'), expected)
    assert_equal(utils.get_share_folder_uri('foo'), expected)


def test_serialize_folder():
    metadata = {
        u'bytes': 0,
        u'icon': u'folder',
        u'is_dir': True,
        u'modified': u'Sat, 22 Mar 2014 05:40:29 +0000',
        u'path': u'/datasets/New Folder',
        u'rev': u'3fed51f002c12fc',
        u'revision': 67032351,
        u'root': u'onedrive',
        u'size': u'0 bytes',
        u'thumb_exists': False
    }
    result = serialize_folder(metadata)
    assert_equal(result['path'], metadata['path'])
    assert_equal(result['name'], 'OneDrive' + metadata['path'])


class TestMetadataSerialization(OsfTestCase):

    def test_metadata_to_hgrid(self):
        metadata = {
            u'bytes': 123,
            u'icon': u'file',
            u'is_dir': False,
            u'modified': u'Sat, 22 Mar 2014 05:40:29 +0000',
            u'path': u'/foo/bar/baz.mp3',
            u'rev': u'3fed51f002c12fc',
            u'revision': 67032351,
            u'root': u'onedrive',
            u'size': u'0 bytes',
            u'thumb_exists': False,
            u'mime_type': u'audio/mpeg',
        }
        node = ProjectFactory()
        permissions = {'view': True, 'edit': False}
        result = utils.metadata_to_hgrid(metadata, node, permissions)
        assert_equal(result['addon'], 'onedrive')
        assert_equal(result['permissions'], permissions)
        filename = utils.get_file_name(metadata['path'])
        assert_equal(result['name'], filename)
        assert_equal(result['path'], metadata['path'])
        assert_equal(result['ext'], os.path.splitext(filename)[1])
