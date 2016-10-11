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
# from website.addons.onedrive.views.config import serialize_folder


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