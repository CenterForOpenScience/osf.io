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
