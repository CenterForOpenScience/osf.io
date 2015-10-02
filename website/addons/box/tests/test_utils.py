# -*- coding: utf-8 -*-
"""Tests for website.addons.box.utils."""
import mock

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from website.project.model import NodeLog

from tests.factories import ProjectFactory

from website.addons.box.tests.utils import BoxAddonTestCase
from website.addons.box import utils
from website.addons.box.serializer import BoxSerializer
from website.addons.box.model import BoxNodeSettings


class TestNodeLogger(BoxAddonTestCase):

    def test_log_file_added(self):
        logger = utils.BoxNodeLogger(
            node=self.project,
            auth=Auth(self.user),
        )
        logger.log(NodeLog.FILE_ADDED, save=True)

        last_log = self.project.logs[-1]

        assert_equal(last_log.action, "box_{0}".format(NodeLog.FILE_ADDED))

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/1557
    def test_log_deauthorized_when_node_settings_are_deleted(self):
        project = ProjectFactory()
        project.add_addon('box', auth=Auth(project.creator))
        dbox_settings = project.get_addon('box')
        dbox_settings.delete(save=True)
        # sanity check
        assert_true(dbox_settings.deleted)

        logger = utils.BoxNodeLogger(node=project, auth=Auth(self.user))
        logger.log(action='node_deauthorized', save=True)

        last_log = project.logs[-1]
        assert_equal(last_log.action, 'box_node_deauthorized')


# TODO(mfraezz): Add support for folder sharing urls
# def test_get_share_folder_uri():
#     expected = 'https://box.com/home/foo?shareoptions=1&share_subfolder=0&share=1'
#     assert_equal(utils.get_share_folder_uri('/foo/'), expected)
#     assert_equal(utils.get_share_folder_uri('foo'), expected)


def test_serialize_folder():
    metadata = {
        u'bytes': 0,
        u'icon': u'folder',
        u'is_dir': True,
        u'modified': u'Sat, 22 Mar 2014 05:40:29 +0000',
        u'path': u'/datasets/New Folder',
        u'rev': u'3fed51f002c12fc',
        u'revision': 67032351,
        u'root': u'box',
        u'size': u'0 bytes',
        u'thumb_exists': False
    }
    result = BoxSerializer().serialize_folder(metadata)
    assert_equal(result['path'], metadata['path'])
    assert_equal(result['name'], 'Box' + metadata['path'])


class TestBoxAddonFolder(BoxAddonTestCase):

    @mock.patch.object(BoxNodeSettings, 'fetch_folder_name', lambda self: 'foo')
    def test_works(self):
        folder = utils.box_addon_folder(
            self.node_settings, Auth(self.user))

        assert_true(isinstance(folder, list))
        assert_true(isinstance(folder[0], dict))

    def test_returns_none_unconfigured(self):
        self.node_settings.folder_id = None
        assert_is(utils.box_addon_folder(
            self.node_settings, Auth(self.user)), None)
