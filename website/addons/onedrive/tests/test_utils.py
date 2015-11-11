# -*- coding: utf-8 -*-
"""Tests for website.addons.onedrive.utils."""
import mock

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from website.project.model import NodeLog

from tests.factories import ProjectFactory

from website.addons.onedrive.tests.utils import OnedriveAddonTestCase
from website.addons.onedrive import utils
from website.addons.onedrive.serializer import OnedriveSerializer
from website.addons.onedrive.model import OnedriveNodeSettings


class TestNodeLogger(OnedriveAddonTestCase):

    def test_log_file_added(self):
        logger = utils.OnedriveNodeLogger(
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
        donedrive_settings = project.get_addon('onedrive')
        donedrive_settings.delete(save=True)
        # sanity check
        assert_true(donedrive_settings.deleted)

        logger = utils.OnedriveNodeLogger(node=project, auth=Auth(self.user))
        logger.log(action='node_deauthorized', save=True)

        last_log = project.logs[-1]
        assert_equal(last_log.action, 'onedrive_node_deauthorized')


class TestOnedriveAddonFolder(OnedriveAddonTestCase):

    @mock.patch.object(OnedriveNodeSettings, 'fetch_folder_name', lambda self: 'foo')
    def test_works(self):
        folder = utils.onedrive_addon_folder(
            self.node_settings, Auth(self.user))

        assert_true(isinstance(folder, list))
        assert_true(isinstance(folder[0], dict))

    def test_returns_none_unconfigured(self):
        self.node_settings.folder_id = None
        assert_is(utils.onedrive_addon_folder(
            self.node_settings, Auth(self.user)), None)
