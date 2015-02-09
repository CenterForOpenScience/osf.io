# -*- coding: utf-8 -*-
"""Tests for website.addons.dropbox.utils."""
import io
import os

from nose.tools import *  # noqa (PEP8 asserts)
from werkzeug.wrappers import Response

from framework.auth import Auth
from website.project.model import NodeLog

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.dropbox.tests.factories import DropboxFileFactory
from website.addons.dropbox.tests.utils import DropboxAddonTestCase
from website.addons.dropbox import utils
from website.addons.dropbox.views.config import serialize_folder


class TestNodeLogger(DropboxAddonTestCase):

    def test_log_file_added(self):
        df = DropboxFileFactory()
        logger = utils.DropboxNodeLogger(
            node=self.project,
            auth=Auth(self.user),
            file_obj=df
        )
        logger.log(NodeLog.FILE_ADDED, save=True)

        last_log = self.project.logs[-1]

        assert_equal(last_log.action, "dropbox_{0}".format(NodeLog.FILE_ADDED))

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/1557
    def test_log_deauthorized_when_node_settings_are_deleted(self):
        project = ProjectFactory()
        project.add_addon('dropbox', auth=Auth(project.creator))
        dbox_settings = project.get_addon('dropbox')
        dbox_settings.delete(save=True)
        # sanity check
        assert_true(dbox_settings.deleted)

        logger = utils.DropboxNodeLogger(node=project, auth=Auth(self.user))
        logger.log(action='node_deauthorized', save=True)

        last_log = project.logs[-1]
        assert_equal(last_log.action, 'dropbox_node_deauthorized')


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


# FIXME(sloria): This test is incorrect. The mocking needs work.
# class TestRenderFile(OsfTestCase):

#     @mock.patch('website.addons.dropbox.client.DropboxClient.get_file_and_metadata')
#     def test_render_dropbox_file_when_file_has_taken_down_by_dmca(self, mock_get_file):
#         mock_resp = mock.Mock(spec=DropboxResponse)
#         mock_resp.reason = 'This file is no longer available due to a takedown request under the Digital Millennium Copyright Act'
#         mock_resp.status = 461
#         mock_client = mock.Mock(spec=DropboxClient)
#         mock_client.get_file_and_metadata.side_effect = ErrorResponse(mock_resp, 'DMCA takedown')
#         with patch_client('website.addons.dropbox.utils.get_node_addon_client', mock_client=mock_client):
#             f = DropboxFileFactory()
#             result = utils.render_dropbox_file(f, client=mock_client)


def test_clean_path():
    assert_equal(utils.clean_path('/'), '/')
    assert_equal(utils.clean_path('/foo/bar/baz/'), 'foo/bar/baz')
    assert_equal(utils.clean_path(None), '')


def test_get_share_folder_uri():
    expected = 'https://dropbox.com/home/foo?shareoptions=1&share_subfolder=0&share=1'
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
        u'root': u'dropbox',
        u'size': u'0 bytes',
        u'thumb_exists': False
    }
    result = serialize_folder(metadata)
    assert_equal(result['path'], metadata['path'])
    assert_equal(result['name'], 'Dropbox' + metadata['path'])


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
            u'root': u'dropbox',
            u'size': u'0 bytes',
            u'thumb_exists': False,
            u'mime_type': u'audio/mpeg',
        }
        node = ProjectFactory()
        permissions = {'view': True, 'edit': False}
        result = utils.metadata_to_hgrid(metadata, node, permissions)
        assert_equal(result['addon'], 'dropbox')
        assert_equal(result['permissions'], permissions)
        filename = utils.get_file_name(metadata['path'])
        assert_equal(result['name'], filename)
        assert_equal(result['path'], metadata['path'])
        assert_equal(result['ext'], os.path.splitext(filename)[1])


